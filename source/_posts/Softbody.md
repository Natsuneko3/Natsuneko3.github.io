---
title: 【UE5】在niagara实现Softbody dynamic
date: 2022-04-08 18:34
tags: Niagara
dplayer: true
category: 文章
cover: https://picx.zhimg.com/v2-fa0f656bfc72e1635473a5a545572c73_1440w.jpg?source=172ae18b
---
最近疫情被锁在家里半个月多月,有点无聊总想搞点什么，就突然想到我模拟这块在niagara上已经做过了基于欧拉视角的NS公式和SPH模拟流体，还有基于PBD的rigid body dynamics，用jocobi迭代隐式积分求解Mass-spring systems，都是基于GPU的效果，无奈niagara是个方便的compute shader，就想着还有什么效果没做过的，就想到个softbody，前面流体的niagara文章在知乎很多大佬都写过，在b站也有解析教程，但反观rigidbody 和softbody的niagara文章比较少，相信有很多对模拟感兴趣同时又想在niagara实现的小伙伴在找文章方面上会走了很多弯路，加上ue5正式版已经发布了，所以就打算写一遍蹭一下热度（笑）

Softbody Dynamic的模拟方法有很多，例如FEM，Mass-spring systems，还有shape matching。由于shape mathcing的方式做起来比较简单，也很合适并行。

{%  dplayer
url="https://vdn6.vzuu.com/SD/4c3e7710-b3c9-11ec-9908-2ed9809c7c79.mp4?pkey=AAUeZfRG71oRoPhIajHYDOfq8fgBdClB2wB8UKRju9gLzZKm-392Yh_wiDPTYG5Mx5H5TPn9rftaS3qmqqLBD0AJ&c=avc.0.0&f=mp4&pu=078babd7&bu=078babd7&expiration=1671272624&v=ks6"
%}

那么先说一下本文做法的步骤。

1. 首先在houdini用撒点把模型变为1024或者512甚至更少，只要是2的幂次方就行，因为是给gpu并行处理。然后记录每个顶点周围4个撒点index信息记录下来
2. 做好constraint，constraint链接方式是每个点向法线*-1就是说向模型内部搜索一个锥型范围，得到点的序号存到一张HDR图里了，x为点的总数，y为当前点的constraint。还要把这512点的position存成512x1的图，
3. 在niagara采样position图生成点，然后在simulate state用GetIndexByID把当前点的index写入grid2d，因为并行时候index是会随时变的，但id是唯一的，所以我们要记住这个粒子的index
4. 做sdf collision
5. 根据公式算出当前要匹配形状的点
6. 对当前的点与要匹配的点做lerp
7. 输出这些点的信息，在材质进行wpo
说完简易的步骤了，接下来说说详细的做法

首先在houdini里


{%  image
url="https://pic2.zhimg.com/80/v2-567cda2cce3817bbf503a92c71bee465_720w.webp"
%}
先建立constraint，用point cloud find找到搜索周围的一圈点，用找到的点减自身对法线做个dot，小于某个值的不要，此时有人会问我，这不是pcopen吗，pcopen就已经有这些功能。其实是因为我太懒了，不想研究pcopen这函数handle怎么用，直接返回一组数我自己找到想要的数据，然后烘培图片，这里做constraint的时候要做多少个，可以自己定义，越多越硬
{%  image
url="https://pic4.zhimg.com/80/v2-dc0f4a68cf1583610821b3ed206c1057_720w.webp"
title=注意geometry file的路径前面要加op
%}
{%  image
url="https://pic4.zhimg.com/80/v2-dc0f4a68cf1583610821b3ed206c1057_720w.webp"
title=position图烘培
%}

最后输出的图一定要为exr，jpg和png会把图片数据限制到0～1

接下来就详细说说shape matching算法

这个算法已经有很多文章写的非常详细，包括games103中也有说过，所以现在按照我的理解再说一下Shape Matching。

首先Shape Matching的思路是把一个刚体不当成一个刚体来看，把每个顶点当成自由的particle，对每个点做单独的碰撞处理，然后再把这些点和他们的约束求MSE（均方误差）恢复到物体原有的形状
{%  image
url="https://pic1.zhimg.com/80/v2-7eb4c0d1a152caf7277b57f36047c42c_720w.webp"
%}

在当前帧，我们要MSE 的表达式比较简单，直接求导数是极值点

其中yi是当前点的位置，c是当前点的位置与他约束(constrain)的质心，R是旋转矩阵
{%  image
url="https://pic2.zhimg.com/80/v2-06a5f0756b58757194604d95f8dff2d5_720w.webp"
%}


整理了以后很容易直观理解，就是对每个点和约束求位置的平均值，再对矩阵求导可得A矩阵，最后我们希望他是恢复到原来的形状，那么我们还要从A矩阵中提取旋转矩阵。
{%  image
url="https://pic3.zhimg.com/80/v2-0f729ef5e4fb4c80978f483a793666ae_720w.webp"
%}

最简单的方法之一是使用极分解，通过对A的分解得到了旋转和形变矩阵，在games103中有见解，但今天要说的方法是另一种

这种方法是源自这篇paper

https://matthias-research.github.io/pages/publications/stablePolarDecomp.pdf

这次说的新方法简单而有效，我们假设我们已经从模拟的上一个时间步或迭代求解的上一步得到一个近似值，而不是直接求解 R。 


其中 exp(ω) 是轴为 ω/|ω| 的旋转矩阵和角度|ω|，也称为指数映射(exponential map)，指数映射可以保证这个矩阵是合适的，既 ω= 0的情况下行列式也等于1，也就说明这个旋转矩阵不会改变物体体积的大小。在这种情况下它假设相同。因此，如果 R 是适当的旋转矩阵，则物体通过update保持不变。

那么我们要怎么选择这个ω的方向呢，最好的选择是用Frobenius范数，因为F范数可以让这个映射矩阵于原始矩阵的差尽可能小，为了找到这个方向，我们以物理方式来解释，让a1，a2,a3为A的列向量，r1,r2,r3为R矩阵的列向量，R矩阵只允许围绕着原点旋转。由于我们想最小化F我们定义的能量


我们将选择 ω 作为刚体在力 EF 下加速的轴。 作用在 R 轴尖端的力为


由于这些力作用在 R 上的总扭矩为


因此，我们为某个标量 α 而选择 ω = ατ。 τ 的引入允许对最小化 Frobenius 范数的矩阵 R 和通过对 矩阵A 进行极分解获得的矩阵 R 进行新的解释。在paper附录中可以证明两者τ = 0。

那么我们怎么选择这个标量α，首先我们来看ai 和 ri，如果我们选择  那么  ,  就是两个向量的角度，然而我们的目标是对齐ai和ri让他们τ = 0，如果|ω| = φ就是完成对齐了，

所以从  得到  所以最终我们产生了迭代公式


其中  是个安全参数，这方法与大多数现有方法相比，它可以粗暴地处理秩亏矩阵 A。在这种情况下，它会继承先前旋转矩阵 R 中的缺失信息。如果 ai 为零，则相应的扭矩分量也为零，并且 R 沿该方向的方向不变。在 A = 0 的极端情况下，总扭矩为零，R 保持不变。如果 a1 是唯一的非零轴，我们的方法会在 r1 和 a1 生成的平面中正确旋转 R 以将 ri 与 a1 对齐。即使 det(A) < 0，R 的行列式也保证保持 =1。

代码如下

    void ExtractRotation(in float3x3 A, inout float4 Q, in uint maxIter)
    {
    float3x3 TA = transpose(A);

        for (uint iter = 0; iter < maxIter; iter++)
        {
            const float3x3 R = transpose(QuatToRotMatrix(Q));

            float3 omega =
                (cross(R[0], TA[0]) + cross(R[1], TA[1]) + cross(R[2], TA[2])) *
                ((1.f / abs(dot(R[0], TA[0]) + dot(R[1], TA[1]) + dot(R[2], TA[2]))) +
                    1.0e-9);

            float w = length(omega);
            if (w < 1.0e-9)
                break;

            Q = QuatMul(float4((1.0 / w) * omega * sin(w * 0.5f), cos(w * 0.5f)), Q);
            Q = normalize(Q);
        }
    }
那么东西都说完，接下来就开始按一开说的大致做

先用id把index记录下来
![](https://pic1.zhimg.com/80/v2-29c6fb6f85ca4d852799ee653197fa30_1440w.webp)

sdf collision就陷入多深就直接给他多少力拉回来，简单粗暴

![](https://pic2.zhimg.com/80/v2-cf1172c0061fa2021de2313351620985_1440w.webp)
更新Shape Matching位置并写入grid2d
{%  image
url="https://pic4.zhimg.com/80/v2-4dae98f35b54fd9561b7dfa2f98ebbd3_1440w.webp"
title=获取当前点和他的约束点的现在位置，然后平均位置，原始点也要，原始点可以直接用initial position
%}
{%  image
url="https://pic4.zhimg.com/80/v2-4dae98f35b54fd9561b7dfa2f98ebbd3_1440w.webp"
title=计算A矩阵
%}
{%  image
url="https://pic3.zhimg.com/80/v2-6982b8b92dd8cb7eceb1ef46b269c76a_1440w.webp"
title=其中Apq就是上面公式的Ai，ShapeMatchingRotation就是R矩阵，最后输出也是他
%}


写完grid2d下个simulation stage 直接读取做lerp
{%  image
url="https://pic4.zhimg.com/80/v2-3382620ecfeace1ca0f54eac209c89a3_1440w.webp"
%}

就这样简单的得到了现在position 和rotation

顺便说个小技巧，写function可以直接写结构体，在结构体里面写，调用这个结构体就行，像材质custom node一样，其中文中里面的旋转矩阵和四元数转换或者四元数相乘都可以从官方节点哪里拿来。