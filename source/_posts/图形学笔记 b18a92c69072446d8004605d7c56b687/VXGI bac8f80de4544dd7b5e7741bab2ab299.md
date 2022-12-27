---
title: VXGI
date: 2022-04-07 12:00
tags: 
- 图形学笔记
- 渲染
category: 笔记
---
# VXGI

Lumen中的VoxelLighting和VXGI类似，使⽤是基于3D Clipmap的⽅式以节省存储空间。但Lumen的VoxelLighting中的每个3D纹素和VXGI中的Voxel并不相同——Lumen的每个3D纹理表⽰的是[Ambient Cube](https://www.notion.so/Ambient-Cube-074e81bf559f43b48fa72e7c2635eae7)某⼀个⽅向上的光照投射参数,实际上它所需要的3D纹素数量是其Size的6倍。这⼉可以看到VoxelLighting选择了和MeshCards⼏乎完全相同的结构(六⾯体)和基函数([AmbientCube](https://www.notion.so/Ambient-Cube-074e81bf559f43b48fa72e7c2635eae7))

VoxelLighting默认使⽤4级3d Clipmap，存储的是以相机世界位置为中⼼点周围200米范围（可配置）的间接光照信息。 所有MipLevels和Directions均直接平铺在⼀张3D纹理中

- 纹理⼤⼩为[64 ,64 * MipLevels ,64 * Directions(6)]，除X轴等同于Clipmap Size外，在Y轴上平铺开了所有MipLevels，在Z轴上平铺开了Ambient Cube的6个⽅向
- 各级Mip表达的距离以指数形式增⻓，第0级表⽰的范围是[0,25米]，第3级是[100米,200米] ,反算其精度，可得第0级的精度为25米*2/64,每个Voxel表达的场景空间⼤约在0.78米，类似可得第3级的精度为3.125米。

对场景执行Voxel Cone Tracing的第一步是构建场景物体的稀疏[体素八叉树](https://www.notion.so/Octrees-89d53e6926b140738b5404d199d64367)（Sparse Voxel Octree），UE5使用了稀疏HLOD的网格距离场

![Untitled](Untitled.png)

![Untitled](Untitled%201.png)

一般使用了混合渲染管线，直接光（Primary ray）使用传统的光栅化获得，次级光则使用椎体追踪在体素椎体追踪之前，会预过滤几何体，然后像参合介质那样去追踪（可使用体积光线投射法）。而体素使用不透明场+入射辐射率来代表场景物体，这样可以使用四线性（Quadrilinearly）插值采样来模拟椎体射线覆盖的脚印

![越后面的用越大的MIP，权重也越小，类似GTAO和SSAO](Untitled%202.png)

越后面的用越大的MIP，权重也越小，类似GTAO和SSAO

Voxel的渲染过程可分拆成3个Pass：第一个Pass是光照，烘焙辐照度（反射阴影图，RSM）；第二个Pass是预过滤，使用稀疏八叉树下采样辐射率；第三个Pass是相机Pass，收集每个可见片元（像素）的辐照度。（下图）

![Untitled](Untitled%203.png)

# 实现Voxel GI

把物体中的颜色信息投影到3d纹理中，需要注意的是塞入到3D纹理中的颜色信息，并不只是物体本身的纹理颜色信息，还需要根据ShadowMap计算这点像素是否被遮挡，同时如果该物体有自发光，也需要将自发光计算在内。这样就构建了一个3D空间下每个像素下的颜色信息。

![Untitled](Untitled%204.png)

需要注意的是，由于一个面上包含的是前后两个面片，为了防止后面的像素被剔除，我们需要Shader的剔除关掉将其设置 Cull Off即可