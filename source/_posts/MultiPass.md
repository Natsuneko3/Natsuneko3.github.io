---
title: 【虚幻引擎】在UE实现多Pass Renderer
date: 2022-06-26 15:38
tags: Engine
category: 文章
cover: https://w.wallhaven.cc/full/yx/wallhaven-yxj26x.jpg
---

# 前言

在ue里面实现多pass比我想象中要简单，并不需要改引擎既可以实现。多pass本质上其实就是模型多画一次，所以ue需要多pass时候只要把模型多复制一份出来就好了，但这样显得有些些蠢，而且drawcall也会增加，所以这篇文章就是介绍基于图元多插入一个或多个Material来实现多pass。

# 讲解

首先介绍一下UE的模型渲染机制
![](https://pic2.zhimg.com/80/v2-c618f31907d85df0d0f17a81e7afc5ed_1440w.webp)
首先可以看到上图，网格体渲染从FPrimitiveSceneProxy开始，FPrimitiveSceneProxy负责通过对GetDynamicMeshElements和DrawStaticElements的回调将FMeshBatch提交给渲染器。从名字就可以看出这个FPrimitiveSceneProxy就是图元场景代理，是UPrimitiveComponent在渲染器的代表，镜像了UPrimitiveComponent在渲染线程的状态。

UE渲染大致的过程是渲染器会遍历场景的所有经过了可见性测试的PrimitiveSceneProxy对象，利用其接口收集不同的FMeshBatch，加入渲染队列中，所以我们自定义自己的渲染数据类型只需要继承FPrimitiveSceneProxy创建FMeshBatch就可以。这里只是粗略的介绍了渲染机制，更加详细的话可以看这篇文章


{% links %}
- site: 博客园
  owner: 0向往0
  url: https://www.cnblogs.com/timlly/p/14588598.html#322-%E4%BB%8Efprimitivesceneproxy%E5%88%B0fmeshbatch
  desc: 剖析虚幻渲染体系（03）- 渲染机制
  image: https://common.cnblogs.com/logo.svg
  color: "#e9546b"
  {% endlinks %}

FPrimitiveSceneProxy有两个生成FMeshBatches的路径：动态路径和缓存路径，就是GetDynamicMeshElements和DrawStaticElements这两个函数去生成FMeshBatches，然后FPrimitiveSceneProxy通过GetViewRelevance(）函数控制每个帧使用的路径。

缓存路径每一帧不会重构，可以缓存FMeshBatches，比如Static Mesh，性能好，但可拓展性弱，当一个FPrimitiveSceneProxy被添加到场景中时会调用此函数。然后储存到FPrimitiveSceneInfo::StaticMeshes中，之后通过AddToDrawLists将FPrimitiveSceneInfo里面的东西交给渲染列表。

动态路径会每帧动态重建FMeshBatch数据，因此可拓展性强，例如ProceduralMesh、waterbody、地形、粒子特效、骨骼动画这些，但效率最低

由FPrimitiveSceneProxy::GetViewRelevance决定由那个途径生成FMeshBatch，其中还有其他关于渲染属性的一些开关：

```c++ ""
uint32 bStaticRelevance : 是否静态路劲生成
uint32 bDynamicRelevance : 是否动态路劲生成
uint32 bDrawRelevance : 是否要渲染
uint32 bShadowRelevance : 是否产生投影
uint32 bVelocityRelevance : 是否要产生速度，用于motion blur或者其他计算
uint32 bRenderCustomDepth : 是否自定义深度
uint32 bRenderInDepthPass : 是否渲染到DepthPass，即使不渲染到MainPass
uint32 bRenderInMainPass : 是否渲染到MainPass
uint32 bEditorPrimitiveRelevance : 仅在编辑器中绘制，并在后期处理后合成到场景中
uint32 bEditorVisualizeLevelInstanceRelevance : 图元的元素属于一个 LevelInstance，它在可视化 LevelInstance 过程中再次被编辑和渲染
uint32 bEditorStaticSelectionRelevance :被选中时候再次渲染OutlinePass
uint32 bEditorNoDepthTestPrimitiveRelevance : 仅在编辑器中绘制，并在后期处理后合成到场景中，不适用深度测试
uint32 bHasSimpleLights : 图元收集简单的灯光是否被GatherSimpleLights 调用
uint32 bUsesLightingChannels : 是否使用灯光Channels
uint32 bTranslucentSelfShadow : 是否使用半透明自阴影
```
还有一些在4.25以上改名的开关 
```c++ ""
UE_DEPRECATED(4.25, "ShadingModelMaskRelevance has been renamed ShadingModelMask")
uint16 ShadingModelMaskRelevance;
UE_DEPRECATED(4.25, "bOpaqueRelevance has been renamed bOpaque")
uint32 bOpaqueRelevance : 1;
UE_DEPRECATED(4.25, "bMaskedRelevance has been renamed bMasked")
uint32 bMaskedRelevance : 1;
UE_DEPRECATED(4.25, "bTranslucentVelocityRelevance has been renamed bOutputsTranslucentVelocity")
uint32 bTranslucentVelocityRelevance : 1;
UE_DEPRECATED(4.25, "bDistortionRelevance has been renamed bDistortion")
uint32 bDistortionRelevance : 1;
UE_DEPRECATED(4.25, "bSeparateTranslucencyRelevance has been renamed bSeparateTranslucency")
uint32 bSeparateTranslucencyRelevance : 1;
UE_DEPRECATED(4.25, "bNormalTranslucencyRelevance has been renamed bNormalTranslucency")
uint32 bNormalTranslucencyRelevance : 1;
UE_DEPRECATED(4.25, "bHairStrandsRelevance has been renamed bHairStrands")
uint32 bHairStrandsRelevance : 1；
```

# 实现

简单介绍完FPrimitiveSceneProxy，然后接了下来说一下实现，为了代码从简，直接用DrawStaticElements，什么情况都不考虑直接用lod0 这部分可以参考StaticMeshRender.cpp,SkeletalMesh则可以参考SkeletalMesh.cpp
```c++ Myproxy
class FMultiDrawSceneProxy : public FPrimitiveSceneProxy
{
public:
   FMultiDrawSceneProxy(UMultiDrawMeshComponent* InComponent)
      : FPrimitiveSceneProxy(InComponent)
        , MultiDrawMeshComponent(InComponent)
   {
   }

   UMultiDrawMeshComponent* MultiDrawMeshComponent;
//每个继承FPrimitiveSceneProxy都要重写这个函数
   virtual uint32 GetMemoryFootprint(void) const { return (sizeof(*this) + GetAllocatedSize()); }

   SIZE_T GetTypeHash(void) const override
   {
      static size_t UniquePointer;
      return reinterpret_cast<size_t>(&UniquePointer);
   }
//静态绘制列表
   virtual void DrawStaticElements(FStaticPrimitiveDrawInterface* PDI) override
   {
//获取RenderData
      const FStaticMeshRenderData* RenderData = MultiDrawMeshComponent->StaticDrawMesh->GetRenderData();
      const FStaticMeshLODResources& Lods = RenderData ->LODResources[0];
//要加的Pass，在Component里面加TArray<UMaterialInterface*>
      int DrawMaterialNum = MultiDrawMeshComponent->DrawMaterial.Num();
      int DrawPassNum = 0;
//重新注册Mesh空间
      PDI->ReserveMemoryForMeshes(1);
//每个材质加一个Pass
      for (UMaterialInterface* MaterialIndex : MultiDrawMeshComponent->DrawMaterial)
      {
         DrawPassNum++;
         FMaterialRenderProxy* MaterialProxy;
//防止第一个材质是空的，用默认材质
         if (MaterialIndex && RenderData)
         {
            if (MaterialIndex == NULL && DrawPassNum == 1)
            {
               MaterialProxy = UMaterial::GetDefaultMaterial(MD_Surface)->GetRenderProxy();
            }
            MaterialProxy = MaterialIndex->GetRenderProxy();

//各种数据设置
            FMeshBatch Mesh;
            FMeshBatchElement& BatchElement = Mesh.Elements[0];
            BatchElement.IndexBuffer = (FIndexBuffer*)&Lods.IndexBuffer;
            Mesh.VertexFactory = &RenderData->LODVertexFactories[0].VertexFactory;
            Mesh.MaterialRenderProxy = MaterialProxy;

            BatchElement.FirstIndex = 0;
            BatchElement.NumPrimitives = Lods.IndexBuffer.GetNumIndices() / 3;
            BatchElement.MinVertexIndex = 0;
            BatchElement.MaxVertexIndex = Lods.IndexBuffer.GetNumIndices() - 1;
            Mesh.ReverseCulling = IsLocalToWorldDeterminantNegative();

            if (DrawPassNum > 1)
            {
               if (MultiDrawMeshComponent->bNeedBackCull)
               {
                  //反向剔除就是front cull,这个可以根据需求来
                  Mesh.ReverseCulling = true;
               }
               Mesh.CastShadow = MultiDrawMeshComponent->bNeedOtherCastShadow;
            }
            //Mesh.bWireframe = true;
            Mesh.Type = PT_TriangleList;
            Mesh.DepthPriorityGroup = SDPG_World;
            Mesh.LODIndex = 0;
//DrawMesh
            PDI->DrawMesh(Mesh,RenderData->ScreenSize[0].GetValue());

         }
      }
   }
//设置各种开关要继承
   virtual FPrimitiveViewRelevance GetViewRelevance(const FSceneView* View) const override
   {
      FPrimitiveViewRelevance Result;
      Result.bDrawRelevance = IsShown(View);
      Result.bShadowRelevance = IsShadowCast(View);
      Result.bDynamicRelevance = false;
      Result.bStaticRelevance = true;
      Result.bRenderInMainPass = ShouldRenderInMainPass();
      Result.bRenderInDepthPass = ShouldRenderInDepthPass();
      Result.bUsesLightingChannels = GetLightingChannelMask() != GetDefaultLightingChannelMask();
      Result.bRenderCustomDepth = ShouldRenderCustomDepth();
      Result.bTranslucentSelfShadow = bCastVolumetricTranslucentShadow;
      Result.bVelocityRelevance = DrawsVelocity() && Result.bOpaque && Result.bRenderInMainPass;

      return Result;
   }

   virtual bool CanBeOccluded() const override { return true; }
   uint32 GetAllocatedSize(void) const { return (FPrimitiveSceneProxy::GetAllocatedSize()); }



};
```
一个最简单的FPrimitiveSceneProxy就完成了，然后实现我们的component


```c++ 头文件
UCLASS(editinlinenew,
   meta = (BlueprintSpawnableComponent),
   ClassGroup = Rendering,
   HideCategories = (Physics, Object, Activation, "Components|Activation"),
   meta = (DisplayName = "MultiDrawMesh"))
class MULTIPASSDRAW_API UMultiDrawMeshComponent : public UMeshComponent
{
   GENERATED_BODY()
public:
   UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MultiDraw Static Mesh")
   class UStaticMesh* StaticDrawMesh;

   UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MultiDraw Static Mesh")
   TArray<UMaterialInterface*> DrawMaterial;

   UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MultiDraw Static Mesh")
   bool bNeedBackCull = false;

   UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MultiDraw Static Mesh",meta=(Displayname = "Need Other Cast Shadow"))
   bool bNeedOtherCastShadow = false;
   
   virtual void GetUsedMaterials(TArray<UMaterialInterface*>& OutMaterials, bool bGetDebugMaterials = false) const override;
   virtual bool GetMaterialStreamingData(int32 MaterialIndex, FPrimitiveMaterialInfo& MaterialData) const override;
   virtual void GetStreamingRenderAssetInfo(FStreamingTextureLevelContext& LevelContext, TArray<FStreamingRenderAssetPrimitiveInfo>& OutStreamingRenderAssets) const override;
   virtual class UBodySetup* GetBodySetup() override{return nullptr;}
   //这个要重新算bound，不然不选择模型的时候会闪
   virtual FBoxSphereBounds CalcBounds(const FTransform& LocalToWorld) const;
   


public:
//放到场景时候会调用这函数
   virtual FPrimitiveSceneProxy* CreateSceneProxy() override;
```

```c++ cpp
FPrimitiveSceneProxy* UMultiDrawMeshComponent::CreateSceneProxy()
{
   if (StaticDrawMesh)
   {
      if (!StaticDrawMesh->GetRenderData()->IsInitialized())
      {
         UE_LOG(LogStaticMesh, Verbose,
                TEXT("Skipping CreateSceneProxy for StaticMeshComponent %s (RenderData is not initialized)"),
                *GetFullName());
         return nullptr;
      }
      return new FMultiDrawSceneProxy(this);
   }

   return nullptr;
}

void UMultiDrawMeshComponent::GetUsedMaterials(TArray<UMaterialInterface*>& OutMaterials, bool bGetDebugMaterials) const
{
	for (UMaterialInterface* material : DrawMaterial)
		OutMaterials.Add(material);
}

bool UMultiDrawMeshComponent::GetMaterialStreamingData(int32 MaterialIndex, FPrimitiveMaterialInfo& MaterialData) const
{
	MaterialData.Material = GetMaterial(MaterialIndex);
	MaterialData.UVChannelData = StaticDrawMesh->GetUVChannelData(MaterialIndex);
	MaterialData.PackedRelativeBox = PackedRelativeBox_Identity;
	return MaterialData.IsValid();
}

void UMultiDrawMeshComponent::GetStreamingRenderAssetInfo(FStreamingTextureLevelContext& LevelContext,
                                                          TArray<FStreamingRenderAssetPrimitiveInfo>&
                                                          OutStreamingRenderAssets) const
{
	GetStreamingTextureInfoInner(LevelContext, nullptr, GetComponentTransform().GetMaximumAxisScale(),
	                             OutStreamingRenderAssets);
}




FBoxSphereBounds UMultiDrawMeshComponent::CalcBounds(const FTransform& LocalToWorld) const
{
	if (StaticDrawMesh)
	{
		FBoxSphereBounds MeshBounds = StaticDrawMesh->GetBounds();
		return MeshBounds.TransformBy(LocalToWorld);
	}
	FBoxSphereBounds DummyBounds = FBoxSphereBounds(FVector(0, 0, 0), FVector(0, 0, 0), 0);
	return DummyBounds.TransformBy(LocalToWorld);
}
```
一个非常简单的component就完成了，更多情况可以参考StaticMeshComponent.h和SkeletalMeshCompnent.h

在drawcall方面分别用了复制四个模型和自己的Component放到场景对比

最后测试出来的结果是
![](https://pic3.zhimg.com/80/v2-63666e2a6c49732188d3121b15342322_1440w.webp
"四个为17drawcall"
)
![](https://pic2.zhimg.com/80/v2-eead240e4769d987f583be639445968d_1440w.webp
"四个为17drawcall"
)
