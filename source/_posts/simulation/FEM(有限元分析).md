---
title: FEM(有限元分析)
date: 2022-04-07 12:00
count: true
tags: 
- 模拟
- 笔记
category: 模拟笔记
---
# FEM(有限元分析)

![Untitled](Untitled.png)

![Untitled](Untitled%201.png)

![Untitled](Untitled%202.png)

![Untitled](Untitled%203.png)

X10 ，x20,x30竖向量写入矩阵，逆矩阵后行列式*1/6是四面体面值

大X是形变前，小x是形变后
矩阵的迹是对角线相加
µ和λ自定义输入，为摩擦力
F0 = -f1 -f2-f3;

```glsl unity文件
using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using System;
using System.IO;

public class FVM : MonoBehaviour
{
    public bool LaplacianSmoothing = false;
    public enum PartType{BasePart, Bonus}
    public PartType partType = PartType.BasePart;

    float dt = 0.0015f;
    float mass = 1;
    float stiffness_0 = 20000.0f;
    float stiffness_1 = 5000.0f;
    float damp = 0.999f;

    float restitution = 0.4f;                   // for collision

    Vector3 gravity = new Vector3(0, -9.8f, 0);

    int[] Tet;
    int tet_number;         //The number of tetrahedra

    Vector3[] Force;
    Vector3[] V;
    Vector3[] SmoothV;
    bool[] isSmooth;
    Vector3[] X;
    int number;             //The number of vertices

    Matrix4x4[] inv_Dm;
    float[] V_ref;
    int[][] neighbour;

    //For Laplacian smoothing.
    Vector3[] V_sum;
    int[] V_num;

    SVD svd = new SVD();

    // Start is called before the first frame update
    void Start()
    {
        // FILO IO: Read the house model from files.
        // The model is from Jonathan Schewchuk's Stellar lib.
        {
            string fileContent = File.ReadAllText("Assets/Lab/lab3/house2.ele");
            string[] Strings = fileContent.Split(new char[] { ' ', '\t', '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);

            tet_number = int.Parse(Strings[0]);
            Tet = new int[tet_number * 4];

            for (int tet = 0; tet < tet_number; tet++)
            {
                Tet[tet * 4 + 0] = int.Parse(Strings[tet * 5 + 4]) - 1;
                Tet[tet * 4 + 1] = int.Parse(Strings[tet * 5 + 5]) - 1;
                Tet[tet * 4 + 2] = int.Parse(Strings[tet * 5 + 6]) - 1;
                Tet[tet * 4 + 3] = int.Parse(Strings[tet * 5 + 7]) - 1;
            }
        }
        {
            string fileContent = File.ReadAllText("Assets/Lab/lab3/house2.node");
            string[] Strings = fileContent.Split(new char[] { ' ', '\t', '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            number = int.Parse(Strings[0]);
            X = new Vector3[number];
            for (int i = 0; i < number; i++)
            {
                X[i].x = float.Parse(Strings[i * 5 + 5]) * 0.4f;
                X[i].y = float.Parse(Strings[i * 5 + 6]) * 0.4f;
                X[i].z = float.Parse(Strings[i * 5 + 7]) * 0.4f;
            }
            //Centralize the model.
            Vector3 center = Vector3.zero;
            for (int i = 0; i < number; i++) center += X[i];
            center = center / number;
            for (int i = 0; i < number; i++)
            {
                X[i] -= center;
                float temp = X[i].y;
                X[i].y = X[i].z;
                X[i].z = temp;
            }
        }
        /*tet_number=1;
        Tet = new int[tet_number*4];
        Tet[0]=0;
        Tet[1]=1;
        Tet[2]=2;
        Tet[3]=3;

        number=4;
        X = new Vector3[number];
        V = new Vector3[number];
        Force = new Vector3[number];
        X[0]= new Vector3(0, 0, 0);
        X[1]= new Vector3(1, 0, 0);
        X[2]= new Vector3(0, 1, 0);
        X[3]= new Vector3(0, 0, 1);*/

        //Create triangle mesh.
        Vector3[] vertices = new Vector3[tet_number * 12];
        int vertex_number = 0;
        for (int tet = 0; tet < tet_number; tet++)
        {
            vertices[vertex_number++] = X[Tet[tet * 4 + 0]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 2]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 1]];

            vertices[vertex_number++] = X[Tet[tet * 4 + 0]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 3]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 2]];

            vertices[vertex_number++] = X[Tet[tet * 4 + 0]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 1]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 3]];

            vertices[vertex_number++] = X[Tet[tet * 4 + 1]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 2]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 3]];
        }

        int[] triangles = new int[tet_number * 12];
        for (int t = 0; t < tet_number * 4; t++)
        {
            triangles[t * 3 + 0] = t * 3 + 0;
            triangles[t * 3 + 1] = t * 3 + 1;
            triangles[t * 3 + 2] = t * 3 + 2;
        }
        Mesh mesh = GetComponent<MeshFilter>().mesh;
        mesh.vertices = vertices;
        mesh.triangles = triangles;
        mesh.RecalculateNormals();

        V = new Vector3[number];
        SmoothV = new Vector3[number];
        isSmooth = new bool[number];
        Force = new Vector3[number];
        V_sum = new Vector3[number];
        V_num = new int[number];

        //TODO: Need to allocate and assign inv_Dm
        inv_Dm = new Matrix4x4[tet_number];
        V_ref = new float[tet_number];
        for (int tet = 0; tet < tet_number; tet++)
        {
            inv_Dm[tet] = Build_Edge_Matrix(tet);
            inv_Dm[tet] = inv_Dm[tet].inverse;
            V_ref[tet] = 1 / (6 * inv_Dm[tet].determinant);
        }
        neighbour = new int[number][];
    }

    Matrix4x4 Build_Edge_Matrix(int tet)
    {
        Matrix4x4 ret = Matrix4x4.zero;
        //TODO: Need to build edge matrix here.

        int index_0 = Tet[tet * 4 + 0];
        int index_1 = Tet[tet * 4 + 1];
        int index_2 = Tet[tet * 4 + 2];
        int index_3 = Tet[tet * 4 + 3];

        Vector3 X10 = X[index_1] - X[index_0];
        Vector3 X20 = X[index_2] - X[index_0];
        Vector3 X30 = X[index_3] - X[index_0];

        ret[0] = X10[0];
        ret[1] = X10[1];
        ret[2] = X10[2];

        ret[0, 1] = X20[0];
        ret[1, 1] = X20[1];
        ret[2, 1] = X20[2];

        ret[0, 2] = X30[0];
        ret[1, 2] = X30[1];
        ret[2, 2] = X30[2];

        ret[3, 3] = 1;
        return ret;
    }

    void _Update()
    {
        // Jump up.
        if (Input.GetKeyDown(KeyCode.Space))
        {
            for (int i = 0; i < number; i++)
                V[i].y += 0.2f;
        }

        Parallel.For(0, number, (i) =>
        {
            //TODO: Add gravity to Force.
            Force[i] = new Vector3(0, -9.8f, 0);
            
        });
        Parallel.For(0, tet_number, (tet) =>
        {
            //TODO: Deformation Gradient
            Matrix4x4 F = Matrix4x4.zero;
            F = Build_Edge_Matrix(tet) * inv_Dm[tet];

            Matrix4x4 P;
            if (partType == PartType.BasePart)
            {
                //TODO: Green Strain
                Matrix4x4 FtF = F.transpose * F;

                Matrix4x4 G = MatrixMultiple(MatrixSubtraction(FtF, Matrix4x4.identity), 0.5f);
                //TODO: Second PK Stress
                float trace;
                trace = G[0, 0] + G[1, 1] + G[2, 2];
                Matrix4x4 dWdG = MatrixAddition(MatrixMultiple(G, 2 * stiffness_1), MatrixMultiple(Matrix4x4.identity, stiffness_0 * trace));

                P = F * dWdG;
            }
            else
            {
                //TODO: Principal stretches 
                Matrix4x4 Lambda = Matrix4x4.identity;
                Matrix4x4 U = Matrix4x4.identity;
                Matrix4x4 V = Matrix4x4.identity;
                svd.svd(F,ref U,ref Lambda,ref V);
                U[3, 3] = 1;
                Lambda[3, 3] = 1;
                V[3, 3] = 1;
                
                Matrix4x4 diag = Matrix4x4.identity;
                float Lambda0 = Lambda[0, 0];
                float Lambda0_2 = Lambda0 * Lambda0;
                float Lambda1 = Lambda[1, 1];
                float Lambda1_2 = Lambda1 * Lambda1;
                float Lambda2 = Lambda[2, 2];
                float Lambda2_2 = Lambda2 * Lambda2;

                diag[0, 0] = 2 * stiffness_0 * (Lambda0_2 + Lambda1_2 + Lambda2_2 - 3) * Lambda0 + stiffness_1 * (Lambda0-1) * Lambda0;
                diag[1, 1] = 2 * stiffness_0 * (Lambda0_2 + Lambda1_2 + Lambda2_2 - 3) * Lambda1 + stiffness_1 * (Lambda1-1) * Lambda1;
                diag[2, 2] = 2 * stiffness_0 * (Lambda0_2 + Lambda1_2 + Lambda2_2 - 3) * Lambda2 + stiffness_1 * (Lambda2-1) * Lambda2;
                //TODO: First PK Stress

                P = U * diag * V.transpose;
            }
            //TODO: Elastic Force

            Matrix4x4 F123 = MatrixMultiple(P, -V_ref[tet]) * inv_Dm[tet].transpose;

            Vector3 f1 = (Vector3)F123.GetColumn(0);
            Vector3 f2 = (Vector3)F123.GetColumn(1);
            Vector3 f3 = (Vector3)F123.GetColumn(2);

            Vector3 f0 = -f1 - f2 - f3;

            Force[Tet[tet * 4 + 0]] += f0;
            Force[Tet[tet * 4 + 1]] += f1;
            Force[Tet[tet * 4 + 2]] += f2;
            Force[Tet[tet * 4 + 3]] += f3;

            if(LaplacianSmoothing)
            {
                int index_0 = Tet[tet * 4 + 0];
                int index_1 = Tet[tet * 4 + 1];
                int index_2 = Tet[tet * 4 + 2];
                int index_3 = Tet[tet * 4 + 3];
                Vector3 v = (V[index_0] + V[index_1] + V[index_2] + V[index_3]) / 4;
                SmoothV[index_0] = v;
                SmoothV[index_1] = v;
                SmoothV[index_2] = v;
                SmoothV[index_3] = v;
            }
        });
        Parallel.For(0, number, (i) =>
        //for (int i = 0; i < number; i++)
        {
            //TODO: Update X and V here.
            if(LaplacianSmoothing)
                V[i] = SmoothV[i];
            V[i] += Force[i] * dt;
            isSmooth[i] = false;
            SmoothV[i] = Vector3.zero;
            X[i] += V[i] * dt;
            V[i] *= damp;
            //TODO: (Particle) collision with floor.
            
        });
        Collision_Impulse(new Vector3(0, -3, 0), new Vector3(0, 1, 0));
    }
   

    void Collision_Impulse(Vector3 P, Vector3 N)
    {
        for (int i = 0; i < V.Length; i++)
        {
            float sdf = PlaneSignedDistanceFunction(X[i], P, N);
            if (sdf < 0)
            {
                if (Vector3.Dot(V[i], N) < 0)
                {
                    Vector3 v_Ni = Vector3.Dot(V[i], N) * N;
                    Vector3 v_Ti = V[i] - v_Ni;
                    float mu_N = restitution;
                    float mu_T = 0.1f;
                    float a = Mathf.Max(1 - (mu_T * (1 + mu_N) * v_Ni.magnitude / v_Ti.magnitude), 0);
                    v_Ni = -mu_N * v_Ni;
                    v_Ti = a * v_Ti;
                    Vector3 v_new_i = v_Ni + v_Ti;

                    V[i] = v_new_i;

                    X[i] = X[i] - sdf * N;
                }
            }
        }
    }

    float PlaneSignedDistanceFunction(Vector3 x, Vector3 P, Vector3 N)
    {
        return Vector3.Dot((x - P), N);
    }

    // Update is called once per frame
    void Update()
    {
        for (int l = 0; l < 10; l++)
            _Update();

        // Dump the vertex array for rendering.
        Vector3[] vertices = new Vector3[tet_number * 12];
        int vertex_number = 0;
        for (int tet = 0; tet < tet_number; tet++)
        {
            vertices[vertex_number++] = X[Tet[tet * 4 + 0]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 2]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 1]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 0]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 3]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 2]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 0]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 1]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 3]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 1]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 2]];
            vertices[vertex_number++] = X[Tet[tet * 4 + 3]];
        }
        Mesh mesh = GetComponent<MeshFilter>().mesh;
        mesh.vertices = vertices;
        mesh.RecalculateNormals();
    }

    Matrix4x4 MatrixSubtraction(Matrix4x4 m1, Matrix4x4 m2)
    {
        m1[0, 0] -= m2[0, 0];
        m1[0, 1] -= m2[0, 1];
        m1[0, 2] -= m2[0, 2];

        m1[1, 0] -= m2[1, 0];
        m1[1, 1] -= m2[1, 1];
        m1[1, 2] -= m2[1, 2];

        m1[2, 0] -= m2[2, 0];
        m1[2, 1] -= m2[2, 1];
        m1[2, 2] -= m2[2, 2];

        m1[3, 3] = 1;
        return m1;
    }

    Matrix4x4 MatrixAddition(Matrix4x4 m1, Matrix4x4 m2)
    {
        m1[0, 0] += m2[0, 0];
        m1[0, 1] += m2[0, 1];
        m1[0, 2] += m2[0, 2];
               
        m1[1, 0] += m2[1, 0];
        m1[1, 1] += m2[1, 1];
        m1[1, 2] += m2[1, 2];
        
        m1[2, 0] += m2[2, 0];
        m1[2, 1] += m2[2, 1];
        m1[2, 2] += m2[2, 2];

        m1[3, 3] = 1;
        return m1;
    }
    Matrix4x4 MatrixMultiple(Matrix4x4 m, float k)
    {
        m[0, 0] *= k;
        m[0, 1] *= k;
        m[0, 2] *= k;
                  
        m[1, 0] *= k;
        m[1, 1] *= k;
        m[1, 2] *= k;
                
        m[2, 0] *= k;
        m[2, 1] *= k;
        m[2, 2] *= k;

        m[3, 3] = 1;
        return m;
    }

}
```