---
title: Visibility Buffer
date: 2022-04-07 12:00
count: true
tags: 
- 图形学笔记
- 渲染
category: 图形学笔记
---
# Visibility Buffer

Visibility Buffer解决了传统延迟渲染的几个问题：

1. 带宽高；
2. 对于可见性和着色阶段的不完美的分离，会造成Overdraw；
3. 不能使用MSAA。

---

Visibility Buffer通常需要这些信息：

（1）**InstanceID**，表示当前像素属于哪个Instance（16~24 bits）；

（2）**PrimitiveID**，表示当前像素属于Instance的哪个三角形（8~16 bits）；

（3）**Barycentric Coord**，代表当前像素位于三角形内的位置，用重心坐标表示（16 bits）；

（4）**Depth Buffer**，代表当前像素的深度（16~24 bits）；

（5）**MaterialID**，表示当前像素属于哪个材质（8~16 bits）；

以上，我们只需要存储大约**8~12 Bytes/Pixel**即可表示场景中所有几何体的材质信息，同时，我们需要维护一个**全局的顶点数据和材质贴图表**，表中存储了当前帧所有几何体的顶点数据，以及材质参数和贴图。在光照着色阶段，只需要根据InstanceID和PrimitiveID从全局的Vertex Buffer中索引到相关三角形的信息；进一步地，根据像该素的重心坐标，对Vertex Buffer内的顶点信息（UV，Tangent Space等）进行插值得到逐像素信息；再进一步地，根据MaterialID去索引相关的材质信息，执行贴图采样等操作，并输入到光照计算环节最终完成着色，有时这类方法也被称为**Deferred Texturing**。

---

VBuffer管线有三个阶段：

- Visibility Passes： 对场景进行光栅化，将Primitive ID和Instance ID（或Material ID）保存到ID Texture里（顺手做个Depth Prepass），也就是说只有可见的Primitive才会进入后续的阶段；
- Worklist Pass：构建并Worklist，这一步是为了驱动下一步，将屏幕划分成很多tile，根据使用到某个Material ID的tile加到该Material ID的Worklist里，作为下一步的索引；
- Shading Passes : 使用Compute Shader对每个Material ID进行软光栅，获取顶点属性并插值，然后再进行表面着色。

![Untitled](Untitled.png)

直观地看，Visibility Buffer减少了着色所需要信息的储存带宽，此外，它将光照计算相关的几何信息和贴图信息读取延迟到了着色阶段，于是那些屏幕不可见的像素不必再读取这些数据，而是只需要读取顶点位置即可。基于这两个原因，**Visibility Buffer在分辨率较高的复杂场景下，带宽开销相比传统G-Buffer大大降低**。但同时维护全局的几何、材质数据，增加了引擎设计的复杂度，同时也降低了材质系统的灵活度，有时候还需要借助Bindless Texture等尚未全硬件平台支持的Graphics API，不利于兼容。