---
title: Lumen
date: 2022-04-19 12:00
count: true
tags:
- 图形学笔记
- 渲染
category: 图形学笔记
---
# Lumen

Lumen是各种GI技术的整合，可以简单概括成SDF(Mesh距离场 + 全局距离场) + “体素”（Surface Cache） + SSGI （屏幕空间追踪）+ RSM (Reflective Shadow Map) + 硬件光追（lumen补充）

SDF(Mesh距离场 + 全局距离场): 软光追加速结构，其中Mesh距离场在UE4里已被用于DFAO，而全局距离场是一张合并了相附近所有Mesh距离场的texture，为了避免遍历每个网格距离场的一种“低配”方案; 这俩正好对应项目设置里的两种追踪模式：Detail Tracing和Global Tracing
Detail Tracing ：前两米内的追踪使用Mesh距离场，其余范围使用Global Tracing
Global Tracing：只追全局距离场，这种性能当然更省，质量也低一些
Surface Cache： 软光追直接和间接光的容器，类似于体素，Nanite网格会加速捕获
SSGI：屏幕空间追踪，这个就不说了，UE4就在用，lumen里作为软光追的补充
RSM（反射阴影贴图）：Surface Cache只覆盖相机200m范围，解决快速移动时软光追的间接光跟不上，此时只有屏幕追踪的情况
硬件光追：也是作为lumen里软光追的补充，Nanite网格需要设置Proxy Triangle Percent生成代理Mesh，再用代理Mesh做硬件光追

**⼀个MeshCard就是⼀个⻓宽⾼不等的且只有⼀个坐标轴朝向 Orientation ∈ [-x,+x,-y,+y,-z,+z]的六⾯体。**从形状上来说，它就是⽅块形的积⽊，这些捕捉位置被称为Cards，是逐网格被离线生成的

通过控制台参数`r.Lumen.Visualize.CardPlacement 1`可以查看Lumen Cards的可视化效果

![3C2A07F8-0199-4CBD-A349-29AAD2119D46.jpeg](3C2A07F8-0199-4CBD-A349-29AAD2119D46.jpeg)

![3172BFC9-626D-458C-AE1E-E21E1F6B7661.jpeg](3172BFC9-626D-458C-AE1E-E21E1F6B7661.jpeg)

![它的核心思想和步骤在于将网格离散化成大小相等的3D体素，然后根据分辨率大小从摄像机位置向每个像素位置发射一条光线和3D体素相交测试，从而渲染出高度场的轮廓。而高度场的轮廓将屏幕划分为高度场覆盖区域和高度场以上区域的分界线](Untitled.png)

它的核心思想和步骤在于将网格离散化成大小相等的3D体素，然后根据分辨率大小从摄像机位置向每个像素位置发射一条光线和3D体素相交测试，从而渲染出高度场的轮廓。而高度场的轮廓将屏幕划分为高度场覆盖区域和高度场以上区域的分界线

![Untitled](Untitled%201.png)

## Lumen在运⾏时有四个主要⼯作来完成最终的GI计算：

- 更新LumenScene（LumenScene即为Lumen在计算过程中所使⽤的场景，它不同于渲染时的FScene结构，它是FScene的⼀个不完整的简化版本）
- 注入直接和间接Diffuse光照到光照缓存中(包括MeshCards和基于3D Clipmap的Voxel等)。根据Lumen场景的Card信息，追踪并更新对应的纹素（Texel）。
- 基于当前屏幕空间⾃动化放置Probe及Trace得到Probe的光照信息，对Probe的光照信息进⾏⼆次编码及⽣成Irradniance Cahe
- 使⽤Probe的光照信息、⼆次编码的光照信息及Irradiance Cache信息计算最终Indirect DIffuse和Indirect Reflection，并混合History光照信息做为最终的GI输出

# ****更新LumenScene****

- 新Primitive加入场景,多Instance如ISM等会进⾏LumenCard合并 --> 新的MeshCards ，DF 加入
- LumenScene已有Primitive从场景中被卸掉 --> Dirty MeshCards ,DF 被从LumenScene移除
- Primitive有更新 --> 更新MeshCards ,DF的Transform/Lod等数据
- 为MeshCards分配和更新其在材质、光照信息等AtlasTexture中的位置和⼤⼩
- 把近处未捕获过材质参数的MeshCards加入渲染列表(默认的近处指的是离相机200米内的所有MeshCards，且要求MeshCards的包围盒⼤于给定阈值，也限制了每帧渲染的MeshCards不超过给定数量,在此做了分帧处理)

![Untitled](Untitled%202.png)

Cache近处MeshCards对应静态模型的渲染指令(DrawCommands)和Nanite的渲染列表，⽤于捕获材质属性(MateialAttributes)，其中静态模型使⽤最⼤的Lod Level⽤于节省材质捕获的开销LumenScene中把场景划分为远景和近景两部分，故除Primitive外，场景中的相机移动也会触发LumenScene更新

****捕获MeshCards的材质属性(MaterialAttributes)****

- Material Albdo ，⽤于⽀持Diffuse Lighting的计算
- Material Emissive ，⽤于⽀持⾃发光照亮场景
- Material Opacity ,⽤于处理光线穿过和在半透物体上的半弹
- Normal ,⽤于光照模型计算各类光照
- DepthStencil ,在Lumen后续的各个阶段均有应⽤，如⽤于计算放置Probe点，⽤于计算光照插值权重等

每个MeshCards当作一个view，把LumenScene光栅化(bound里面的东西)，走navite流程，把Basecolor、Normal、Emissions分别写到他们的Atlas(图集)上

![Untitled](Untitled%203.png)

在完成材质属性捕获操作后，还会执⾏以下操作:

- 计算Depth的矩(Moments)并⽣成Mipmap ,⽤于后续Trace时使⽤切比雪夫不等式估算Occlusion，这⼀处理⽅式来源于Variance Shadow Maps3，也在DDGI4中被⽤来处理Irradiance Volume的可⻅性。
- 预处理Opacity和⽣成Mipmpa链

****注入光照到缓存(Inject Lighting To Cache)****

在完成MeshCards数据更新及材质属性捕获之后，下⼀步就是需要把当前场景中的光照信息注入到光照缓存中去。Lumen使⽤了三种主要的数据结构来缓存场景中的光照信息，它们分别是MeshCards和其对应的AtlasTexture(最⾼精度)、Voxel 3D Clipmap2(中精度)和GI Volume（⽤于体渲染）。这三种类型的数据同时可以

覆盖场景中的静态物体、动态物体和体渲染的物体，可形成完成的GI照明来源

![Untitled](Untitled%204.png)

# ****Voxel Cone Tracing****

[VXGI](https://www.notion.so/VXGI-bac8f80de4544dd7b5e7741bab2ab299)

# ****为MeshCards注入光照****

从上⾯的流程图可知，MeshCards的光照注入分为直接光和间接光两部分，且直接光和间接光也都只计算Diffuse贡献⽽不计算&Specular贡献。

第⼀步是先计算MeshCards的间接光，间接光的计算可以按光照源数据来源，Trace⽅式两个维度进⾏拆分，Lumen共⽀持4种不同的间接光计算模式，

![Untitled](Untitled%205.png)

Lumen使⽤VoxelLighting做为间接光的来源并使⽤分块Trace复⽤来计算MeshCard的间接照明。

逐纹素采样⽣成的Indirect Lighting具有更⾼的精度，但需要更多的采样点从⽽性能更差，基于分块的Trace因为复⽤相邻纹素的采样结果，所以在⼤多数情况下可以使⽤更少的采样数量达到更平滑的采样结果

关于间接光的Voxel Trace部分的简要说明

- 使⽤Global Distance Field进⾏加速求交
- 使⽤的是Voxel ConeTrace采样VoxelLighting,默认的每个纹素采样8个Cone，根据Hit距离确定使⽤哪⼀级Mipmap
- 采样的Cone同时会采样天光(如果天光开启)叠加到Lighting结果中

第⼆步是对间接光的结果再次进⾏Bilinear Filter并过滤掉<0的异常值

第三步是计算直接光照的贡献，Lumen⽀持的直接光类型包括: PointLight 、SpotLight 、RectLight和DirectionalLight。除DirectionalLight是逐盏灯计算外外，其它三种类型的光照都是分批执⾏的——因为它们光照范围有限，可以只把这⼀批次内影响的MeshCards找出来，每批次的直接光渲染只对在他们影响范围内的MeshCards⽣效。直接光计算的最后⼀个要点是：只计算Diffuse贡献项。

# ****更新VoxelLighting Mips，Voxel光照注入****

从上⾯VoexlLighting介绍⼀节可以看到它是⼀个以相机世界位置为中⼼点的Voxel Clipmap,这样在相机发⽣移动时，Clipmap也同样需要进⾏更新。为减少单次需要更新的Voxel数量，有如下优化。

[1]. 保证每帧最多更新⼀级Mips,Voxel Clipmap四级Mip更新的的顺序如下如⽰:

a. 第 0 , 2 , 4 , 6 , 8 ,... 帧允许更新第0级mip

b. 第 1 , 5 , 9 , 13 , 17 ,... 帧 允许更新第1级mip

c. 第 3 , 11 , 19 , 27 , ... 帧 允许更新第2级mip

d. 第 7 , 15 , 23 , 31 , ... 帧 允许更新第3级mip

[2]. 在相机未发⽣剧烈移动时，理论上只需要更新移动⽅向上影响部分的Voxel

除了相机更新，场景中的Primitive增删修改也会影响到它周围的Voxel，所以这个策略实际上在Lumen的实作中采⽤的是更⼀般的PrimitiveUpdateBounds去和Clipmap Tile Bound求交，来确定真正需要更新的Voxel数量，更新的也不是Voxel，⽽是接下来会介绍到的VisibilityBuffer

VoxelLighting光照解算过程使⽤MeshDistanceField来加速求交：Lumen选择的是先使⽤当前Voxel Clipmap的Boundbox去剔除掉不在此范围内的所有Objects及其对应的MeshDistanceField, 再使⽤这些通过剔除的MeshDistanceField包围盒来计算它们⾃⼰所覆盖了哪些Voxel并把⾃⼰的索引写入所有覆盖Voxel的Trace参数中，在接下来的Voxel Trace Pass⾥，每个Voxel仅需处理上⼀步所填入的MeshDistanceFiled即可。Voxel Trace Pass的输出数据是包含HitDistance和HitObjectIndex组合的VisibilityBuffer。VisibilityData

最后的Voxel Shading Pass则从压缩过的VisibilityBuffer中获取到最佳的三张MeshCard来⽤对Voxel解算光照，这⼉计算光照的权重系数不只使⽤AmbientCube的系数，同时考虑到物体的透明度和MeshCard的可⻅性。权重Weight的计算公式如下所⽰

```cpp
VisibilityWeight= 1.0f;
vec2 DepthMoments;//来源于Material Attribute Capture float NormalizedDistanceToHit ; //hit distanceif (NormalizedDistanceToHit> DepthMoments.x)
{
float Variance= abs(Square(DepthMoments.x)- DepthMoments.y); VisibilityWeight= saturate(Variance/ (Variance+Square(NormalizedDistanceToHit- DepthMoments.x)));

constfloat VisibilityCutoff= 0.15f;
    VisibilityWeight= (VisibilityWeight- VisibilityCutoff)/ (1.0f- VisibilityCutoff);
}

float Weight= AmbientCubeWeight* VisibilityWeight* Opacity
```

# 生**成和计算GIVolume**

此处的GIVolume即为传统Irradiance Volume，其默认覆盖离相机距离80米的世界(z轴)。实现要点如下：

- 光源来⾃于VoxelLighting ,使⽤ConeTrace解决光照，
- 默认的每个Volume采样16个Cone使⽤SH2编码每个最终结果
- 除VoxelLighting外每个ConeTrace也会采样天光会混合历史光照数据，产⽣更平滑的变化

# ****ScreenSpace Probe与Indirect Lighting解算****

1. 光源：把场景分为近景和远景，近景使⽤VoxelLighting，远景使⽤DistantMeshCard（相当于⼀个巨⼤的AmbientCube)
2. 光照计算：使⽤PixelWorldPosition和PixelWorldNormal获取最近且⽅向匹配的3个Voxel来解算当前GI
3. 效率： 可以使⽤半屏或更⼩分辨率的GI RenderTarget
4. 效果： 使⽤spatial和temporal Filter平滑光照，使⽤⼀些粗糙的⼿段处理漏光（比如Normal offset,限制墙体厚度，使⽤stencil标记室内外，使⽤SDF推采样点到物体外等等）

Lumen是⼀个综合性的基于软件Trace的GI⽅案，它同时使用了SSGI，Detail MeshCard Trace, VoxelLighting Trace，Distant Meshcard Trace四种方式去求解最终光照，其中各种Trace的作用距离和优先性排列如下：

- SSGI 的作用范围是全场景的，即只要SSGI可以Trace到Hit则使用SSGI的反弹信息
- Detail MeshCard Trace的作用起始范围在距离不超过2米,Trace距离不超过离相机40米，和计算VoexLighting时⼀样的⽅式在采样MeshCard 光照信息时会使⽤类似VSM的⽅式使⽤概率估算遮挡
- VoxelLighting Trace的作用范围只覆盖了离相机200米以内的像素范围，遮挡估算是基于Cone实施的
- Distant MeshCard Trace作用范围在200~1000米范围内，这个精度下遮挡估算已然⽆意义
- 半透物体的处理有⽣成GI Volume(？未查证实现是否真引⽤GIVolume)
    
    ![Untitled](Untitled%206.png)
    
    ![很容易看到在室外场景中，主要是靠VoxelLighting照明的。](Untitled%207.png)
    
    很容易看到在室外场景中，主要是靠VoxelLighting照明的。
    
    Lumen选择的是使⽤当前帧屏幕像素所对应的世界位置来放置Probe，并为之命名为ScreenSpace Probe。Probe采⽤八⾯体映射(OctahedralMap)6存储,默认⼤⼩为8*8。这既⽅便使⽤⼀张2D的RenderTarget来做为Atlas Texture存储所有的Probe,同时八⾯体映射⼜没有椭圆映射存在的边界接缝难以处理的问题。八⾯体映射从2D纹理到球⾯和半球的映射过程如下图所⽰，更详细的算法描述⻅：
    
    [](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.681.1522&rep=rep1&type=pdf)
    
    ![Untitled](Untitled%208.png)
    
    有了Probe之后，Lumen的Indirect Diffuse解算流程调整如下:
    
    ![Untitled](Untitled%209.png)
    
    1.Downsample屏幕⼤⼩到1/16,1/16 + 1/32，其中[1/16,1/16]部分均均⽣成Probe，剩下的[1/16,1/32]根据周围probe的空间信息来和⾃适应⽣成。其中uniform placement⼀个pass按16像素距离 + jitter 放置， adaptive placment部分分两个pass,分别按8像素和4像素的距离进⾏迭代，查找需要放置probe的位置。adaptive placement的算法可描述为:
    
    ```
    sample周围4个probe {sample_probe(uv) , uv|uv+ [(0,0),(1,0),(0,1),(1,1)]}
    计算bilinear weight
    获取这些probe和当前position的深度差和夹⾓, 计算depth weight& corner weight 叠加
    biliner weight成finalWeight
    如果所有 finalWeight< 0 ，说明周围没有有效的Probe可以采样，则放置⼀个新的probe
    ```
    
    2. 使⽤ConeTrace采样MeshCard和VoxelLighting及SSGI⽣成probe的radiance、对probe做sptial filter和修复边界上的采样点，转⼀份probe到基于SH的数据但并不清理掉原始的probe数据，这样，probe实际上存在两份radiance数据——octahedral map + sh双料存储
    
    3. upsample probe到屏幕⼤⼩，temporal blend Indirect Diffuse。upsample有两个主要分⽀:
    
    - 对于非hair stand的像素使⽤第2步中⽣成的Probe SH,使⽤adaptive palcement相同的权重进⾏SH混合计算最终光照
    - 对于hair会使⽤brdf importance sample weight,采样Probe cotahedral map进⾏混合计算最终光照
    
    如果不使⽤rtx reflection,同⼀个pass中还会进⾏indirect specular的解算，最后把indirect diffuse和上⼀帧的indirect diffuse进⾏混合，做为最终indirect diffuse输出。这样就完成整个Lumen GI的计算⼯作。可以看到的是Lumen在整个流程中没有像RTX⼀样，依赖很重的时频域Filter来压像素间的⽅差。
    

# Lumen总结

# **Lumen的⽆限反弹是如何实现的？**

Meshcard采样的VoxelLighting是上⼀帧的数据,这样MeshCards反弹数据会从第⼆帧开始累积，每帧都会多⼀次反弹。

[剖析虚幻渲染体系（06）- UE5特辑Part 2（Lumen和其它）](https://www.cnblogs.com/timlly/p/15007236.html)