---
title: 阴影渲染机制
date: 2023-01-30 12:00
tags:
- 笔记
- UE源码
category: UE源码笔记
count: true
---

# 阴影初始化

阴影初始化`InitDynamicShadows`的主要过程，如下：

- 根据view、场景光源、控制台变量初始化阴影相关标记。
- 遍历场景所有光源（Scene->Lights），执行以下操作：
    - 如果光源没有开启阴影或阴影质量太小，或者光源在所有view都不可见，忽略之，不执行阴影投射。
    - 如果是点光源全景阴影，则将该光源组件名字加入Scene的UsedWholeScenePointLightNames列表中。
    - 如果符合全景阴影的创建条件，调用CreateWholeSceneProjectedShadow：
        - 初始化阴影数据，计算阴影所需的分辨率、过渡因子（FadeAlpha）等。
        - 若过渡因子太小（小于1/256），则直接返回。
        - 遍历光源的投射阴影数量，每次都执行分辨率计算、位置（SizeX、SizeY）计算、需创建的阴影图数量等。
            - 根据阴影图数量创建同等个数的FProjectedShadowInfo阴影实例，对每个阴影实例：
                - 设置全景投射参数（视锥体边界、变换矩阵、深度、深度偏移等）、过渡因子、缓存模式等。
                - 加入VisibleLightInfo.MemStackProjectedShadows列表；如果是单通道点光源阴影，填充阴影实例的cubemap6个面的数据（视图投影矩阵、包围盒、远近裁剪面等），并初始化锥体。
                - 对非光追距离场阴影，执行CPU侧裁剪。构建光源视图的凸面体，再遍历光源的移动图元列表，调用IntersectsConvexHulls让光源包围盒和图元包围盒求交测试，相交的那些图元才会添加到阴影实例的主体图元列表中。对光源的静态图元做相似的操作。
                - 最后将需要渲染的阴影实例加入VisibleLightInfo.AllProjectedShadows列表中。
    - 针对两类光源（移动和固定的光源、尚未构建的静态光源）创建CSM（级联阴影）。调用AddViewDependentWholeSceneShadowsForView创建视图关联的CSM：
        - 遍历所有view，针对每个view：
            - 如果不是主view，直接跳过后续步骤。
            - 获取视图相关的全景投影数量，创建同等数量的FProjectedShadowInfo阴影实例，给每个阴影实例设置全景投影参数，最后添加到阴影实例列表和待裁剪列表中。
    - 处理交互阴影（指光源和图元之间的影响，包含PerObject阴影、透明阴影、自阴影等），遍历光源的动态和静态图元，给每个图元调用SetupInteractionShadows设置交互阴影：
        - 处理光源附加根组件，设置相关标记。如果存在附加根组件，跳过后续步骤。
        - 如果需要创建阴影实例，则调用CreatePerObjectProjectedShadow创建逐物体阴影：
            - 遍历所有view，收集阴影相关的标记。
            - 如果本帧不可见且下一帧也没有潜在可见，则直接返回，跳过后续的阴影创建和设置。
            - 没有有效的阴影组图元，直接返回。
            - 计算阴影的各类数据（阴影视锥、分辨率、可见性标记、图集位置等）。
            - 若过渡因子（FadeAlpha）小于某个阈值（1.0/256.0），直接返回。
            - 符合阴影创建条件且是不透明阴影，则创和设置建阴影实例，加入VisibleLightInfo.MemStackProjectedShadows列表中。如果本帧可见则加入到阴影实例的主体图元列表，如果下一帧潜在可见则加入到VisibleLightInfo.OccludedPerObjectShadows的实例中。
            - 符合阴影创建条件且是半透明阴影，执行上步骤类似操作。
- 调用InitProjectedShadowVisibility执行阴影可见性判定：
    - 遍历场景的所有光源，针对每个光源：
        - 分配视图内的投射阴影可见性和关联的容器。
        - 遍历可见光源所有的阴影实例，针对每个阴影实例：
            - 保存阴影索引。
            - 遍历所有view，针对每个view：
                - 处理视图关联的阴影，跳过那些不在视图视锥内的光源。
                - 计算主体图元的视图关联数据，断阴影是否被遮挡，设置阴影可见性标记。
                - 如果阴影可见且不是RSM，利用FViewElementPDI绘制阴影锥体。
- 调用UpdatePreshadowCache清理旧的预计算阴影，尝试增加新的到缓存中：
    - 初始化纹理布局。
    - 遍历所有缓存的预阴影, 删除不在此帧渲染的实例。
    - 收集可以被缓存的PreShadow列表。
    - 对PreShadow从大到小排序（更大的PreShadow在渲染深度时会有更多的物体）。
    - 遍历所有未缓存的PreShadow，尝试从纹理布局中给PreShadow找空间，若找到，则设置相关数据并添加到Scene->CachedPreshadows列表中。
- 调用GatherShadowPrimitives收集图元列表，以处理不同类型的阴影：
    - 如果没有PreShadow且没有视图关联的全景阴影（ViewDependentWholeSceneShadows），则直接返回。
    - 如果允许八叉树遍历（GUseOctreeForShadowCulling决定），利用八叉树遍历Scene->PrimitiveOctree，针对每个孩子节点：
        - 检查孩子节点是否至少在一个阴影（包含PreShadow和视图相关的全景阴影）内，如果是，则push到节点容器中。
        - 如果图元节点的元素大于0，从FMemStack创建一个FGatherShadowPrimitivesPacket实例，将该节点的相关数据存入其中，添加到FGatherShadowPrimitivesPacket实例列表中。
    - 如果是非八叉树遍历模式，则线性遍历图元，创建FGatherShadowPrimitivesPacket并加入到列表中。
    - 利用ParallelFor并行地过滤掉和阴影不相交的图元，收集和阴影相交的图元。
    - 收集最后阶段，将受阴影影响的图元加入阴影实例的SubjectPrimitive列表中，清理之前申请的资源。
- 调用AllocateShadowDepthTargets分配阴影图所需的渲染纹理：
    - 初始化不同类型的指定了分配器的阴影列表。
    - 遍历所有光源，针对每个光源：
        - 遍历光源的所有阴影实例，针对每个阴影实例：
            - 检测阴影是否至少在一个view中可见。
            - 检测阴影缓存模式为可移动图元时的条件可见性。
            - 其它特殊的可见性判断。
            - 如果阴影可见，根据不同类型加入到不同的阴影实例列表中。
        - 排序级联阴影，因为在级联之间的混合要求是有序的。
        - 调用AllocateCSMDepthTargets分配CSM深度渲染纹理。
        - 处理PreShadow。
        - 依次分配点光源cubemap、RSM、缓存的聚光灯、逐物体、透明阴影的渲染纹理。
        - 更新透明阴影图的uniform buffer。
        - 删除完全没有被使用的阴影缓存。
- 调用GatherShadowDynamicMeshElements收集阴影的动态网格元素：
    - 遍历所有阴影图图集（ShadowMapAtlases），收集每个图集内的所有阴影实例的网格元素。
    - 遍历所有RSM阴影图图集（RSMAtlases），收集每个图集内的所有阴影实例的网格元素。
    - 遍历所有点光源立方体阴影图（ShadowMapCubemaps），收集每个立方体阴影图内的所有阴影实例的网格元素。
    - 遍历所有PreShadow缓存的阴影图（PreshadowCache），收集阴影实例的网格元素。
    - 遍历所有透明物体阴影图图集（TranslucencyShadowMapAtlases），收集每个图集内的所有阴影实例的网格元素。

## **优化技巧**：

- 利用物体（视图、光源、阴影、图元）的简单形状做相交测试，剔除不相交的阴影元素。
- 利用各类标记（物体、视图、控制台、全局变量等等）及衍生标记，剔除不符合的阴影元素。
- 利用中间数据（过渡因子、屏幕尺寸大小、深度值等等）剔除不符合的阴影元素。
- 特殊数据结构（纹理布局、阴影图集、八叉树、连续线性数组）和遍历方式（并行、八叉树、线性）提升执行效果。
- 充分利用缓存（PreShadowCache、潜在可见性等）减少渲染效果。
- 对阴影类型进行排序，减少渲染状态切换，减少CPU和GPU交互数据，提升缓存命中率。
- 不同粒度的遮挡剔除。

# 渲染阴影

阴影应用阶段可以关注几个重要步骤和额外说明：

- 每个开启了阴影且拥有有效阴影的光源都会渲染一次`ScreenShadowMaskTexture`。
- 渲染`ScreenShadowMaskTexture`前，会调用ClearShadowMask清理`ScreenShadowMaskTexture`，保证`ScreenShadowMaskTexture`是原始状态（全白）。
- 调用`RenderShadowProjections`，将光源下的所有阴影实例投射并叠加到**屏幕空间**的`ScreenShadowMaskTexture`。这样做的目的是类似于延迟着色，将多个阴影提前合并到View的视图空间，以便后续光照阶段只需要采样一次即可得到阴影信息，提升渲染效率。缺点是要多一个Pass来合并光源的阴影，增加了Draw Call，也增加了少量的显存消耗。
- `ScreenShadowMaskTexture`除了常规的对比深度图阴影，还可能包含距离场阴影、次表面阴影、透明体积阴影、胶囊体阴影、高度场阴影、头发阴影、RT阴影等类型。它的每个通道都有特殊的用途，用于细分和存储不同类型的阴影信息。意思就是`ScreenShadowMaskTexture`就是所有类型已经渲染出来的阴影的结合
- 渲染`ScreenShadowMaskTexture`的shader在过滤阴影图时，支持三种过滤方式：无过滤、PCSS和自定义PCF。
- 在光照计算的shader中，`ScreenShadowMaskTexture`被绑定到`LightAttenuationTexture`（光照衰减纹理）的变量中，亦即C++层的ScreenShadowMaskTexture其实就是光照Shader的`LightAttenuationTexture`。
- 在光照Shader文件`DeferredLightPixelShaders`.usf中，计算动态光照时，只调用一次了`GetPerPixelLightAttenuation`()的值（亦即只采样一次`LightAttenuationTexture`），即可计算出物体表面受阴影影响的光照结果。

总结阴影渲染主要流程：

| 初始化阴影 | 渲染灯光深度图 | 渲染ScreenShadowMaskTexture | 采样LightAttenuationTexture（ScreenShadowMaskTexture） | 计算表面阴影 | 计算表面光照 |
| --- | --- | --- | --- | --- | --- |
| InitDynamicShadows | RenderShadowDepthMaps | RenderShadowProjections | GetPerPixelLightAttenuation | GetShadowTerms | GetDynamicLighting |
