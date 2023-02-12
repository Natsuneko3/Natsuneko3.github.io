---
title: Virtual Texture解析
date: 2023-02-03 12:00
tags:
- 笔记
- UE源码
- Virtual Texture
category: UE源码笔记
count: true
---
# Virtual Texture解析

1. `FVirtualTextureSystem`是整个Virtual Texture 的管理类，几乎所有的VT系统的操作都会通过他来进行调度。
2. `FVirtualTextureSpace`用来管理Page table的，其数量上有明显的上限，只有16个。一个Page table资源对应一个FVirtualTextureSpace对象。这里限制的原因应该是标志位的限制，我们在FeedBack中仅有4位留给我们判断属于哪个Page table。
3. `FVirtualTexturePhysicalSpace`用来管理Physical Texture部分。Physical Texture的数量是没有限制的。引擎会把所有拥有相同`FVTPhysicalSpaceDescription`且没有勾选`bSinglePhysicalSpace`(主要用于RVT)的将放入一个PhysicalSpace。这个过程是引擎自动判断的，需要注意的是，share PhysicalSpace和share Pagetable是矛盾的，因为share PhysicalSpace就意味着Physical Address不能是一样的，所以Page Table无法share（但可以分布在一个texture的不同channel里）。
4. `FAdaptiveVirtualTexture` 用来管理Indirect 部分。在后面我们讲到。

整个Virtual Texture 的流程几乎都在各自renderer中体现出来。在Render中主要的步骤其实有三步

1. 在Render开始阶段对`FVirtualTextureSpace`管理的固定数量的Page table进行判断，通过`bNeedToAllocatePageTable`看是否需要渲染资源的创建。也就是创建新的Page table资源，这个page table最多16张
2. 更新整个VT系统，包括解析FeedBack，更新pagetable和physical texture。
3. 在Basspass之后，我们读取在Basspass中写入的feedback，供下一帧使用

# FeedBack

FeedBack 是我们分析当前屏幕中，使用VT 的具体情况。UE4 中并没有单独的 VT feedback Pass，而是在材质 Shader 的最后调用 FinalizeVirtualTextureFeedback 将当前帧的 Request Page 信息 写入 feedback UAV Buffer。

从RenderDoc中我们可以看到是在Basepass中进行的写入操作，其默认空值是FFFFFFFF。如果这个物体的材质没有采样VT，那么它就不会写FeedBack，也就是默认值0xFFFFFFFF。

## ****生成FeedBack****

![Untitled](Virtual%20Texture%E8%A7%A3%E6%9E%90/Untitled.png)

1. TableID：FeedBack所在的像素块的纹理对应的PageTable的ID。因为我们在材质中采样这个贴图的时候，我们是知道我们这个pageTable的ID的。（16个PageTable）
2. vPageX：所在PageTable中的X坐标，根据UV，Tile数量和PageTable 偏移求出来。
3. vPageY：所在PageTable中的Y坐标，根据UV，Tile数量和PageTable偏移 求出来。
4. vLevel：这里并不是简单的Mipmap，因此UE换了个名称叫做vLevel。做法是当前的Mipmap+一个随机值，这样的话在静止画面下，这个值实际上是一个区间，每帧我们的vLevel就是不同的，这样，我们就能根据TAA来做一些混合操作。

Feedback是和basepass同时进行的，在Basspass之后我们将回读这个Buffer，提供给下一帧的update进行分析和使用。

# ****Update****

在FVirtualTextureSystem中，最为关键和重要的步骤我们大致分为5个流程来进行。

![Untitled](Virtual%20Texture%E8%A7%A3%E6%9E%90/Untitled%201.png)

## **解析FeedBack**

这里进行将Feedback解析，将其转化位一个名为FUniquePageList的数据结构中。FUniquePageList 内部是一个 Hash Table，通过 hash Page Request 得到 Page 的索引并进行累加次数，进而统计每个Page出现的次数。

![https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210521171404.png](https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210521171404.png)

这里的解析是实际上根据解析数量的不同可以进行多线程的操作，比如规定每一万个数据划分一个线程进行处理。这里我们按单线程的方案进行讲解。

## **生成UniqueRequest**

我们得到的FUniquePageList并不是一个具备操作性的数据集，因为它只记录了出现的Page和Tile出现的次数，我们还需要知道这里面数据的是否需要更新。我们这里将FUniquePageList数据转化为能够为我们提供更多信息的UniqueRequest数据。

![https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210521171410.png](https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210521171410.png)

从上图我们可以看出，整个UniqueRequest内部有多种的请求类型，例如：

1. LoadRequest：这一帧需要画它，需要把这个Tile加载进来。这是用来更新Physical Texture的。
2. MappingRequest：和LoadRequest对应，不过它记录的是用来更新PageTable 的数据，需要在LoadRequest完成后执行。
3. DirectMappingRequest：physical texture存在，直接将 physical address写入PageTable。
4. ContinuousUpdateRequest：在RVT中可以设置，这个Tile是否需要持续更新，每帧都会去更新这个tile。

![https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210521171416.png](https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210521171416.png)

## **加载和sort策略**

![https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210520115144.png](https://papalqiblog.oss-cn-beijing.aliyuncs.com/blog/picture20210520115144.png)

当我们获取了所有的更新数据之后，我们将进行加载排序，这是因为我们需要对加载的优先级进行判断，而不是一股脑的都在同一帧处理大量的数据。如果把所有需求都在同一帧进行加载，这将会导致相当大的卡顿。简单的介绍我们的排序策略。

1. 当Physical Texture没有空间时，我们采用的卸载策略为LRU，优先替换最久未访问并且Mip分辨率最低的Block。我们每帧都会把当前的帧数，根据feedback的返回数据对使用到的Physical Texture进行写入。也就是说每个 Physical Texture都保留最近一次使用到的帧数，从而能够进行判断谁是最久没有被使用到的。
2. 我们每帧最大的加载量为64，我们将计算所有的LoadRequest的优先级，如果一帧里面的请求过多，只接受优先级前64个。
3. 如果想要加载低mipmap，需要加载这个贴图高几个mipmap的贴图。也就是说，我们优先加载比需要的这个贴图mipmap等级高的贴图，这是为了降低渲染压力。物理贴图块会分帧渲染，每帧只渲染一部分Block。当最低级的Mip都没有时，实际上分帧之后加载速度仍然是非常快的，对分帧加载这个过程也是基本无感知的。
4. 如果出现的次数特别多，那么我们会把他设置为我们最高优先级，如果是普通的次数，我们的

## **SubmitRequests和Finalize**

当我们把需要在这一帧操作的request筛选出来后，将提交我们的Requests。其会更新我们的PageTable和Physical Texture。

UE4 并未使用Compute pipeline 来更新 PageTable Texture，而是通过 Graphics Pipeline 在 VS 中生成，在 PS 中存储到 PageTable RenderTarget，并且使用 Instancing Rendering 的方式，最多一次处理 16 个 PageTable Quad，这样处理与 CS 基本相同。

而我们的Physical Texture则根据自己不同的IVirtualTextureFinalizer类型进行不同的Finalize操作。传统的svt对应的`FVirtualTextureUploadCache`将硬盘里的数据直接进行拷贝到对应的Physical Texture区域。而Runtime的`FRuntimeVirtualTextureFinalizer`将会启用RDG渲染那块区域最后进行Copy到对应的Physical Texture区域。

# 采样

`VirtualTexture` 的采样数据跟普通的贴图采样不同。其主要分为两部分，第一部分是获得对应的`PageTable`，第二步是根据`PageTable` 的值采样我们的`physical Texture`。这两个函数操作都是在我们的BasePass中，其中在`TextureLoadVirtualPageTable`中不仅采样整个点的`PageTable`，而且还进行了FeedBack 的写入。我们以RVT位例子。

![Untitled](Virtual%20Texture%E8%A7%A3%E6%9E%90/Untitled%202.png)

> 第一个函数的参数，这个是和材质中这个贴图的一一对应的PageTable。存储在Material uniform 里面。因此我们可以直接进行他的采样。
> 

## TextureLoadVirtualPageTable

通过`TextureComputeVirtualMipLevel` 函数计算 RVT 的 mipLevel，为了实现较好的混合效果，这里根据当前帧 Id 生成交错的随机 noise 扰动 level。4bit 得到 mipLevel，最多 16 级（0~15）

## TextureVirtualSample

![Untitled](Virtual%20Texture%E8%A7%A3%E6%9E%90/Untitled%203.png)