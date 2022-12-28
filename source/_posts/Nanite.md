---
title: Lumen
date: 2022-04-19 12:00
tags:
- 图形学笔记
- 渲染
category: 笔记
---
# Nanite

![Untitled](Untitled.png)

![基于Mesh Shader的Pipeline，Cluster剔除成为了顶点处理阶段的一部分，减少没必要的Vertex Buffer Load/Store](Untitled%201.png)

基于Mesh Shader的Pipeline，Cluster剔除成为了顶点处理阶段的一部分，减少没必要的Vertex Buffer Load/Store

Nanite把实现分成两个过程三个部分: *预处理过程 : 在模型导入或者在引擎中修改模型设置时处理，把高模预处理成一簇簇的三角形簇，建立分层分页结构用于渲染和加载*

![Untitled](Untitled%202.png)

把模型分成Cluster,类似Meshshader中的Meshlet。划分在拓扑空间中邻近的Cluster，是为了提高访问数据时Cache命中率。Cluster分割使用Metis库把模型的顶点数据进一步切分为更细粒度的**Cluster**（或者叫做**Meshlet**），让每个Cluster的粒度能够更好地适应Vertex Processing阶段的Cache大小，并以Cluster为单位进行各类剔除（**Frustum Culling，Occulsion Culling，Backface Culling**）已经逐渐成为了复杂场景优化的最佳实践，

### **Primtive数据**

Nanite资源的Primitive数据都使用StructureBuffer存在于GPU Memory中，这就为后续的剔除、合批等操作提供了GPU Driven式的便利。

### **Cull**

Nanite的Cull在是GPU Driven的，在CS中执行的，它分为两大块： 一是Primitive Instance级，为每个模型执行FrustumCull/HZB Cull 二是内部BVH树及Cluster级，分层的为BVH进行剔除，在一直相交的情形下会下降到Cluster Boundary，注意到目前的Nanite Cluster剔除并没有剔除面积很小的三角形，也没有做背面剔除。 Cull的同时它还会做一件事：标记该三角形走软件光栅化还是走硬件光栅化——只有面积小于给定值的三角形才会走软件光栅化

### **光栅化(Rasterization)**

在剔除结束之后，每个Cluster会根据其屏幕空间的大小送至不同的光栅器，**大三角形和非Nanite Mesh仍然基于硬件光栅化，小三角形基于Compute Shader写成的软光栅化**。Nanite的Visibility Buffer为一张R32G32_UINT的贴图(8 Bytes/Pixel)，其中R通道的0~6 bit存储Triangle ID，7~31 bit存储Cluster ID，G通道存储32 bit深度。

整个软光栅化的逻辑比较简单：基于扫描线算法，每个Cluster启动一个单独的Compute Shader，在Compute Shader初始阶段计算并缓存所有Clip Space Vertex Position到shared memory，而后CS中的每个线程读取对应三角形的Index Buffer和变换后的Vertex Position，根据Vertex Position计算出三角形的边，执行背面剔除和小三角形（小于一个像素）剔除，然后利用原子操作完成Z-Test，并将数据写进Visibility Buffer。

# **软光栅化是否有机会打败硬光栅化？**

**传统光栅化硬件设计之初，设想的输入三角形大小是远大于一个像素的**。基于这样的设想，硬件光栅化的过程通常是**层次式的**。以N卡的光栅器为例，一个三角形通常会经历两个阶段的光栅化：**Coarse Raster**和**Fine Raster**，前者以一个三角形作为输入，以8x8像素为一个块，将三角形光栅化为若干块（你也可以理解成在尺寸为原始FrameBuffer 1/8*1/8大小的FrameBuffer上做了一次粗光栅化）。在这个阶段，借由低分辨率的Z-Buffer，被遮挡的块会被整个剔除，N卡上称之为**Z Cull**；在Coarse Raster之后，通过Z Cull的块会被送到下一阶段做Fine Raster，最终生成用于着色计算的像素。在Fine Raster阶段，有我们熟悉的**Early Z**。由于mip-map采样的计算需要，我们必须知道每个像素相邻像素的信息，并利用采样UV的差分作为mip-map采样层级的计算依据。为此，Fine Raster最终输出的并不是一个个像素，而是2x2的小像素块（**Pixel Quad**）。

对于接近像素大小的三角形来说，硬件光栅化的浪费就很明显了：首先，Coarse Raster阶段几乎是无用的，因为这些三角形通常都是小于8x8的，对于那些狭长的三角形，这种情况更糟糕，因为一个三角形往往横跨多个块，而Coarse Raster不但无法剔除这些块，还会增加额外的计算负担；另外，对于大三角形来说，基于Pixel Quad的Fine Raster阶段只会在三角形边缘生成少量无用的像素，相较于整个三角形的面积，这只是很少的一部分；但对于小三角形来说，**Pixel Quad最坏会生成四倍于三角形面积的像素数**，并且这些像素也包含在pixel shader的执行阶段，使得warp中有效的像素大大减少。

![Untitled](Untitled%203.png)

每次渲染小三角形会形成很多像素的浪费在像素级小三角形这一特定前提下，**软光栅化（基于Compute Shader）的确有机会打败硬光栅化**。这也正是Nanite的核心优化之一，这一优化使得UE5在小三角形光栅化的效率上**提升了3倍**。

# UE5 nanite 流程

它的核心思想可以简单拆解为两大部分：**顶点处理的优化**和**像素处理的优化**。**其中顶点处理的优化主要是GPU Driven Pipeline的思想；像素处理的优化，是在Visibility Buffer思想的基础上，结合软光栅化完成的**

![Untitled](Untitled%204.png)

每个Nanite Mesh在预处理阶段，会被切成若干Cluster，每个Cluster包含128个三角形，其实是一个图的切分（graph partition）。整个Mesh以**BVH（Bounding Volume Hierarchy）**的形式组织成树状结构，每个叶节点代表一个Cluster。剔除分两步，包含了**视锥剔除**和**基于HZB的遮挡剔除**。其中Instance Cull以Mesh为单位，通过Instance Cull的Mesh会将其BVH的根节点送到Persistent Cull阶段进行层次式的剔除

# **如何把Persistent Cull阶段的剔除任务数量映射到Compute Shader的线程数量**？

最简单的方法是**给每棵BVH树一个单独的线程，也就是一个线程负责一个Nanite Mesh**。但由于每个Mesh的复杂度不同，其BVH树的节点数、深度差异很大，这样的安排会导致每个线程的任务处理时长大不相同，线程间互相等待，最终导致并行性很差；**那么能否给每个需要处理的BVH节点分配一个单独的线程呢**？这当然是最理想的情形，但实际上我们无法在剔除前预先知道会有多少个BVH节点被处理，因为整个剔除是层次式的、动态的。Nanite解决这个问题的思路是：设置固定数量的线程，每个线程通过一个全局的FIFO任务队列去取BVH节点进行剔除，若该节点通过了剔除，则把该节点的所有子节点也放进任务队列尾部，然后继续循环从全局队列中取新的节点，直到整个队列为空且不再产生新的节点

![Untitled](Untitled%205.png)

# ****Emit Targets****

为了保证数据结构尽量紧凑，减少读写带宽，所有软光栅化需要的数据都存进了一张Visibility Buffer，但是为了与场景中基于硬件光栅化生成的像素混合，我们最终还是需要将Visibility Buffer中的额外信息写入到统一的Depth/Stencil Buffer以及Motion Vector Buffer当中。这个阶段通常由几个全屏Pass组成

### （1）**Emit Scene Depth/Stencil/Nanite Mask/Velocity Buffer**

这一步根据最终场景需要的RenderTarget数据，最多输出四个Buffer，其中Nanite Mask用0/1表示当前像素是普通Mesh还是Nanite Mesh（根据Visibility Buffer对应位置的ClusterID得到），对于Nanite Mesh Pixel，将Visibility Buffer中的Depth由UINT转为float写入Scene Depth Buffer，并根据Nanite Mesh是否接受贴花，将贴花对应的Stencil Value写入Scene Stencil Buffer，并根据上一帧位置计算当前像素的Motion Vector写入Velocity Buffer，非Nanite Mesh则直接discard跳过。

（2）**Emit Material Depth**
这一步将生成一张Material ID Buffer，稍有不同的是，它并未存储在一张UINT类型的贴图，而是将UINT类型的Material ID转为float存储在一张格式为D32S8的Depth/Stencil Target上（稍后我们会解释这么做的理由），理论上最多支持2^32种材质（实际上只有14 bits用于存储Material ID），而Nanite Mask会被写入Stencil Buffer中。

# ****Classify Materials && Emit G-Buffer****

**Nanite的材质Shader是在Screen Space执行的，Nanite在Base Pass绘制阶段并不是每种材质一个全屏Pass，而是将屏幕空间分成若干8x8的块，比如屏幕大小为800x600，则每种材质绘制时生成100x75个块，每块对应屏幕位置。为了能够整块地剔除，在Emit Targets之后，Nanite会启动一个CS用于统计每个块内包含的Material ID的种类。由于Material ID对应的Depth值预先是经过排序的，所以这个CS会统计每个8x8的块内Material Depth的最大最小值作为Material ID Range存储在一张R32G32_UINT的贴图中**

![Untitled](Untitled%206.png)

有了这张图之后，每种材质在其VS阶段，都会根据自身块的位置去采样这张贴图对应位置的Material ID Range，若当前材质的Material ID处于Range内，则继续执行材质的PS；否则表示当前块内没有像素使用该材质，则整块可以剔除，此时只需将VS的顶点位置设置为NaN，GPU就会将对应的三角形剔除。由于通常一个块内的材质种类不会太多，这种方法可以有效地减少不必要的overdraw。实际上通过分块分类减少材质分支

整个Base Pass分为两部分，首先绘制非Nanite Mesh的G-Buffer，这部分仍然在Object Space执行，和UE4的逻辑一致；之后按照上述流程绘制Nanite Mesh的G-Buffer，其中材质需要的额外VS信息（UV，Normal，Vertex Color等）通过像素的Cluster ID和Triangle ID索引到相应的Vertex Position，并变换到Clip Space，根据Clip Space Vertex Position和当前像素的深度值求出当前像素的重心坐标以及Clip Space Position的梯度（DDX/DDY），将重心坐标和梯度代入各类Vertex Attributes中插值即可得到所有的Vertex Attributes及其梯度（梯度可用于计算采样的Mip Map层级）。

![Untitled](Untitled%207.png)

[Epic王祢：详解虚幻引擎5核心技术Nanite](http://www.gamelook.com.cn/2021/10/456369)

Nanite LOD

我们把LOD 0的Mesh拿过来，生成了一组LOD 0的Cluster，那这组Cluster我们会再用graph partition的条件，把一组Cluster，比如64个、32个或者更少的Cluster合并成一个Cluster Group。背后的条件也是一样的，面积尽可能均匀、边界尽可能少，在减面的时候，其实是在这个Group里进行。我先简单举例，如右图所示（实际划分不止是4个），比如现在有一些Cluster、假设它只有4个面，我把这4个Cluster并成了一个Group，这是LOD 0的。那我要降一级LOD的时候怎么做呢？我先把这些Cluster的边界全解开，把一个Group看成一个大的Cluster，这时我锁住这个Cluster的边界，去对半地减面。之后再以128个面分成一个Cluster时，它Cluster的数量刚好也是减半，就变成了两个Cluster，所以生成了新的Cluster Group里减完面的就是两个Cluster。大家可以看到，这两个Cluster除了Group的外边界跟上面保持一致，内部的边界其实是没有关系的。