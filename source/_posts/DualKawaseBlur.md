---
title: 【UE4/UE5】拓展后期pass实现DualKawaseBlur
date: 2022-11-07 17:35
tags: Engine
category: 文章
cover: https://pic1.zhimg.com/v2-79bce61997eaf687cca50c7dabcb3065_1440w.jpg?source=172ae18b
---

# Scene View Extension

在UE4.17的时候官方开放了可以在后期插入自己pass的接口，那么我们就可以写自己的shader，甚至可以写compute shader去做后期处理。还可以做多pass。而且使用方式也很简单

我们只需要继承FSceneViewExtensionBase
```c++
class GAMES202_API FDualKawaseBlur : public FSceneViewExtensionBase
{
public:
   FDualKawaseBlur(const FAutoRegister& AutoRegister) : FSceneViewExtensionBase(AutoRegister)
   {
   }

   virtual void SetupViewFamily(FSceneViewFamily& InViewFamily) override {};
   virtual void SetupView(FSceneViewFamily& InViewFamily, FSceneView& InView) override {};
   virtual void BeginRenderViewFamily(FSceneViewFamily& InViewFamily) override {};
  //输出贴图
   virtual void SubscribeToPostProcessingPass(EPostProcessingPass Pass, FAfterPassCallbackDelegateArray& InOutPassCallbacks, bool bIsPassEnabled) override;
};
```
并且重载3个函数，这个类里面还有很多虚函数可以重写，可以在各个地方执行逻辑
```c++

 virtual void SetupViewFamily(FSceneViewFamily& InViewFamily) = 0;//

//在游戏线程创建view时候调用
virtual void SetupView(FSceneViewFamily& InViewFamily, FSceneView& InView) = 0;

//在创建View时调用，在剔除之前
virtual void SetupViewPoint(APlayerController* Player, FMinimalViewInfo& InViewInfo) {}

//设置Mvp矩阵时候调用
virtual void SetupViewProjectionMatrix(FSceneViewProjectionData& InOutProjectionData) {}

//当view family即将渲染在游戏线程调用
virtual void BeginRenderViewFamily(FSceneViewFamily& InViewFamily) = 0;

//开始渲染view family前调用
virtual void PreRenderViewFamily_RenderThread(FRDGBuilder& GraphBuilder, FSceneViewFamily& InViewFamily) {}

//在渲染线程开始渲染时候调用，对每个视图，在PreRenderViewFamily_RenderThread后调用
virtual void PreRenderView_RenderThread(FRDGBuilder& GraphBuilder, FSceneView& InView) {}

//视图初始化时候调用
virtual void PreInitViews_RenderThread(FRDGBuilder& GraphBuilder) {}

//使用延迟渲染在basePass完成的时候调用
virtual void PostRenderBasePassDeferred_RenderThread(FRDGBuilder& GraphBuilder, FSceneView& InView, const FRenderTargetBindingSlots& RenderTargets, TRDGUniformBufferRef<FSceneTextureUniformParameters> SceneTextures) {}

//使用移动端渲染的basepass完成时候调用
virtual void PostRenderBasePassMobile_RenderThread(FRHICommandListImmediate& RHICmdList, FSceneView& InView) {}

//后期盒子之前调用
virtual void PrePostProcessPass_RenderThread(FRDGBuilder& GraphBuilder, const FSceneView& View, const FPostProcessingInputs& Inputs) {};
```
具体在SceneViewExtension.h

对于在后期插入pass输出贴图我们可以在SubscribeToPostProcessingPass里面注册Delegate，这是个回调函数，ue5会在SSRInput、MotionBlur、Tonemap、FXAA、VisualizeDepthOfField这5个post process pass中有个lambda函数去调用这Delegate并输出我们的pass，而ue4则没有SSRInput和不支持mobile插入pass

{% image
url="https://pic3.zhimg.com/80/v2-1a531f2ec8d8743db843a4803d3457fe_1440w.webp"
title=Postprocess.cpp
%}

在创建好自己的SceneViewExtension类后我可以在新建个蓝图actor类，在actor中新建个函数，直接调用

FSceneViewExtensions::NewExtension，他会自动帮你在引擎注册视图，这样我们就可以启动我们的pass了
```c++
void ASetupDualKawaseBlur::DrawPass()
{
	if(DualKawaseBlur)
	{
		DualKawaseBlur.Reset();
		DualKawaseBlur = FSceneViewExtensions::NewExtension<FDualKawaseBlur>(InOffset,InPassNum,UseGaussianPass);
	}
	else
	{
		DualKawaseBlur = FSceneViewExtensions::NewExtension<FDualKawaseBlur>(InOffset,InPassNum,UseGaussianPass);
	}
}
```

# DualKawaseBlur

DualKawaseBlur的原理也很简单，他是衍生自Kawase 
Blur的模糊算法，而Kawase Blur就是用来做bloom，那DualKawaseBlur的原理就是在降分辨率的同时采样一个像素的四个角做卷积（通俗点就是做平均），做完几张降分辨率的pass后，再做同样pass
的升分辨率的操作并上下左右像素和四个角做卷积

{% image
url="https://pic3.zhimg.com/80/v2-8b00333bd6c99e2fc63a8547caa6c03a_1440w.webp"
title=这个就是图像处理的卷积核，相当于乘当前采样的值并相加
%}
这就是Dual Kawase Blur的过程
{% image
url="https://pic3.zhimg.com/80/v2-e8214e4a4a3a8e1d9191a6b67ee8a096_1440w.webp"
%}
方式还是很简单的
![](https://pic3.zhimg.com/80/v2-1e5eccdacfcfb1799b2df3a7ede49536_1440w.webp)
在性能上表现最佳，效果也是比较接近高斯模糊，相比之下，高斯模糊模糊的值越大，消耗也是成倍增加
{% image
url="https://pic1.zhimg.com/80/v2-419c8a4d584f779076278e9dbc36589c_1440w.webp"
title=DualKawaseBlur 的耗时
%}
{% image
url="https://pic3.zhimg.com/80/v2-6d853687a366a063ff2d902d86101f8a_1440w.webp"
title=高斯模糊的耗时
%}
在用compute shader的情况下，3070ti，差不多同样的效果，高斯模糊竟然达到了20ms，而dual blur只有3个pass才0.2ms

# 源码

最后是代码

DualKawaseBlur.h
```c++
#include "CoreMinimal.h"
#include "SceneViewExtension.h"
#include "ScreenPass.h"
#include "ShaderParameterStruct.h"
//#include "DualKawaseBlur.generated.h"

/**
 * 
 */

class GAMES202_API FDualKawaseBlur : public FSceneViewExtensionBase
{
public:
	FDualKawaseBlur(const FAutoRegister& AutoRegister,float InOffset,int InPassNum,bool InUseGaussian)
		: FSceneViewExtensionBase(AutoRegister),
	Offset(InOffset),
	PassNum(InPassNum)
	{
	}

	virtual void SetupViewFamily(FSceneViewFamily& InViewFamily) override {};
	virtual void SetupView(FSceneViewFamily& InViewFamily, FSceneView& InView) override {};
	virtual void BeginRenderViewFamily(FSceneViewFamily& InViewFamily) override {};//
	//注册函数输出贴图
	virtual void SubscribeToPostProcessingPass(EPostProcessingPass Pass, FAfterPassCallbackDelegateArray& InOutPassCallbacks, bool bIsPassEnabled) override;//
        //逻辑编写
	FScreenPassTexture PostProcessPassAfterTonemap_RenderThread(FRDGBuilder& GraphBuilder, const FSceneView& View, const FPostProcessMaterialInputs& InOutInputs);

	float Offset;
	
	int PassNum = 1;

};
```
DualKawaseBlur.cpp
```c++
// Fill out your copyright notice in the Description page of Project Settings.


#include "DualKawaseBlur.h"
#include "PixelShaderUtils.h"
#include "RenderGraphEvent.h"
#include "ScreenPass.h"
#include "PostProcess/PostProcessing.h"
#include "PostProcess/PostProcessMaterial.h"

//用于提交的降Pass的Compute shader类
class FDualKawaseBlurDCS : public FGlobalShader
{
	DECLARE_GLOBAL_SHADER(FDualKawaseBlurDCS);
	SHADER_USE_PARAMETER_STRUCT(FDualKawaseBlurDCS, FGlobalShader);

	static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& Parameters)
	{
		return IsFeatureLevelSupported(Parameters.Platform, ERHIFeatureLevel::SM5);
	}

//定义环境，可以定义#if和#Define数值
	static void ModifyCompilationEnvironment(const FGlobalShaderPermutationParameters& Parameters,
	                                         FShaderCompilerEnvironment& OutEnvironment)
	{
		FGlobalShader::ModifyCompilationEnvironment(Parameters, OutEnvironment);
		OutEnvironment.SetDefine(TEXT("NUMTHREADS_X"), 32);
		OutEnvironment.SetDefine(TEXT("NUMTHREADS_Y"), 32);
	}

	BEGIN_SHADER_PARAMETER_STRUCT(FParameters,)
		SHADER_PARAMETER(FVector4f, ViewSize)
		SHADER_PARAMETER_STRUCT_REF(FViewUniformShaderParameters, View)
		SHADER_PARAMETER_SAMPLER(SamplerState, Sampler)
		SHADER_PARAMETER_RDG_TEXTURE(Texture2D, Intexture)
		SHADER_PARAMETER_RDG_TEXTURE_UAV(RWTexture2D<float4>, OutTexture)

		END_SHADER_PARAMETER_STRUCT()
};
//用于提交的升Pass的Compute shader类
class FDualKawaseBlurUCS : public FGlobalShader
{
	DECLARE_GLOBAL_SHADER(FDualKawaseBlurUCS);
//声明传参用的宏
	SHADER_USE_PARAMETER_STRUCT(FDualKawaseBlurUCS, FGlobalShader);
//应该编译的环境
	static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& Parameters)
	{
		return IsFeatureLevelSupported(Parameters.Platform, ERHIFeatureLevel::SM5);
	}
        //环境定义，可以定义#if 和#define
	static void ModifyCompilationEnvironment(const FGlobalShaderPermutationParameters& Parameters,
	                                         FShaderCompilerEnvironment& OutEnvironment)
	{
		FGlobalShader::ModifyCompilationEnvironment(Parameters, OutEnvironment);
		OutEnvironment.SetDefine(TEXT("NUMTHREADS_X"), 32);
		OutEnvironment.SetDefine(TEXT("NUMTHREADS_Y"), 32);
	}
//定义传参用的宏
	BEGIN_SHADER_PARAMETER_STRUCT(FParameters,)
		SHADER_PARAMETER(FVector4f, ViewSize)
		SHADER_PARAMETER_STRUCT_REF(FViewUniformShaderParameters, View)
		SHADER_PARAMETER_RDG_TEXTURE(Texture2D, Intexture)
		SHADER_PARAMETER_SAMPLER(SamplerState, Sampler)
		SHADER_PARAMETER_RDG_TEXTURE_UAV(RWTexture2D<float4>, OutTexture)

		END_SHADER_PARAMETER_STRUCT()
};

//compute shader类所对应usf那些函数
IMPLEMENT_GLOBAL_SHADER(FDualKawaseBlurDCS, "/ProjectS/DualKawaseBlur.usf", "DownSampleCS", SF_Compute);
IMPLEMENT_GLOBAL_SHADER(FDualKawaseBlurUCS, "/ProjectS/DualKawaseBlur.usf", "UpSampleCS", SF_Compute);


void FDualKawaseBlur::SubscribeToPostProcessingPass(EPostProcessingPass Pass, FAfterPassCallbackDelegateArray& InOutPassCallbacks, bool bIsPassEnabled)
{
//对应pass枚举
	if (Pass == EPostProcessingPass::MotionBlur)
	{
		InOutPassCallbacks.Add(FAfterPassCallbackDelegate::CreateRaw(this, &FDualKawaseBlur::PostProcessPassAfterTonemap_RenderThread));
	}
}

FScreenPassTexture FDualKawaseBlur::PostProcessPassAfterTonemap_RenderThread(FRDGBuilder& GraphBuilder, const FSceneView& View, const FPostProcessMaterialInputs& InOutInputs)
{
	
	const FScreenPassTexture SceneColor = InOutInputs.Textures[(uint32)EPostProcessMaterialInput::SceneColor];
	const FViewInfo& ViewInfo = static_cast<const FViewInfo&>(View);
	FRDGTextureDesc TextureDesc = SceneColor.Texture->Desc;
	FRDGTextureRef TempTexture = SceneColor.Texture;
	TextureDesc.Flags = ETextureCreateFlags::UAV;
	FScreenPassTexture OutPass;
	
	RDG_EVENT_SCOPE(GraphBuilder, "DualKawaseBlurCompute");
	for (int i = 0; i < PassNum; ++i)
	{
		FScreenPassRenderTarget OutSceneRenderTarget(GraphBuilder.CreateTexture(TextureDesc, TEXT("DluaKawaseDownPass")), ERenderTargetLoadAction::ELoad);

//创建UAV
		FRDGTextureUAVRef Outexture = GraphBuilder.CreateUAV(OutSceneRenderTarget.Texture);
		FDualKawaseBlurDCS::FParameters* PassParameters = GraphBuilder.AllocParameters<FDualKawaseBlurDCS::FParameters>();
		PassParameters->Intexture = TempTexture;
		PassParameters->ViewSize = FVector4f(TextureDesc.Extent.X, TextureDesc.Extent.Y, Offset, 0);
		PassParameters->View = View.ViewUniformBuffer;
		PassParameters->Sampler = TStaticSamplerState<SF_Point, AM_Clamp, AM_Clamp, AM_Clamp>::GetRHI();
		PassParameters->OutTexture = Outexture;
//初始化着色器
		TShaderMapRef<FDualKawaseBlurDCS> ComputeShader(ViewInfo.ShaderMap);
//提交pass
		FComputeShaderUtils::AddPass(GraphBuilder,
		                             RDG_EVENT_NAME("DualKawaseBlurDownSample %dx%d (CS)", Outexture->Desc.Texture->Desc.Extent.X, Outexture->Desc.Texture->Desc.Extent.Y),
		                             ComputeShader,
		                             PassParameters,
		                             FComputeShaderUtils::GetGroupCount(TextureDesc.Extent, FIntPoint(32, 32)));
//降分辨率
		TextureDesc.Extent.X = TextureDesc.Extent.X / 2;
		TextureDesc.Extent.Y = TextureDesc.Extent.Y / 2;
		TempTexture = Outexture->Desc.Texture;
	}
	for (int i = 0; i < PassNum; ++i)
	{
		TextureDesc.Extent.X = TextureDesc.Extent.X * 2;
		TextureDesc.Extent.Y = TextureDesc.Extent.Y * 2;
		FScreenPassRenderTarget OutSceneRenderTarget(GraphBuilder.CreateTexture(TextureDesc, TEXT("DluaKawaseUpPass")), ERenderTargetLoadAction::ELoad);

		FRDGTextureUAVRef Outexture = GraphBuilder.CreateUAV(OutSceneRenderTarget.Texture);
		FDualKawaseBlurUCS::FParameters* PassParameters = GraphBuilder.AllocParameters<FDualKawaseBlurUCS::FParameters>();
		PassParameters->Intexture = TempTexture;
		PassParameters->ViewSize = FVector4f(TextureDesc.Extent.X, TextureDesc.Extent.Y, Offset, 0);
		PassParameters->View = View.ViewUniformBuffer;
		PassParameters->Sampler = TStaticSamplerState<SF_Point, AM_Clamp, AM_Clamp, AM_Clamp>::GetRHI();
		PassParameters->OutTexture = Outexture;

		TShaderMapRef<FDualKawaseBlurUCS> ComputeShader(ViewInfo.ShaderMap);
		FComputeShaderUtils::AddPass(GraphBuilder,
		                             RDG_EVENT_NAME("DualKawaseBlurUpSample %dx%d (CS)", Outexture->Desc.Texture->Desc.Extent.X, Outexture->Desc.Texture->Desc.Extent.Y),
		                             ComputeShader,
		                             PassParameters,
		                             FComputeShaderUtils::GetGroupCount(TextureDesc.Extent, FIntPoint(32, 32)));
		TempTexture = Outexture->Desc.Texture
		OutPass = OutSceneRenderTarget;
	}
	
	if (OutPass.IsValid())
	{
		return MoveTemp(OutPass);
	}
	else
	{
		return SceneColor;
	}
	
}
```

最后新建个actor类编写一个函数，然后在蓝图的构建函数里面调用就可以了
```c++
void ASetupDualKawaseBlur::DrawPass()
{
	if(DualKawaseBlur)
	{
		DualKawaseBlur.Reset();
		DualKawaseBlur = FSceneViewExtensions::NewExtension<FDualKawaseBlur>(InOffset,InPassNum,UseGaussianPass);
	}
	else
	{
		DualKawaseBlur = FSceneViewExtensions::NewExtension<FDualKawaseBlur>(InOffset,InPassNum,UseGaussianPass);
	}
}
```