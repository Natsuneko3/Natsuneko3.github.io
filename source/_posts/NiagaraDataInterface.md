---
title: 使用自定义Niagara数据接口
count: true
date: 2023-01-02 21:50:27
tags: 
- Niagara
- 笔记
category: UE源码笔记
---
# 使用自定义Niagara数据接口
继承自***public UNiagaraDataInterface***
```c++ FNDIMousePositionProxy
struct FNDIMousePositionProxy : public FNiagaraDataInterfaceProxy
{
	virtual int32 PerInstanceDataPassedToRenderThreadSize() const override { return sizeof(FNDIMousePositionInstanceData); }

    //把数据从游戏线程复制到渲染线程
	static void ProvidePerInstanceDataForRenderThread(void* InDataForRenderThread, void* InDataFromGameThread, const FNiagaraSystemInstanceID& SystemInstance)
	{
		// initialize the render thread instance data into the pre-allocated memory
	
		FNDIMousePositionInstanceData* DataForRenderThread = new (InDataForRenderThread) FNDIMousePositionInstanceData();

		// we're just copying the game thread data, but the render thread data can be initialized to anything here and can be another struct entirely
		const FNDIMousePositionInstanceData* DataFromGameThread = static_cast<FNDIMousePositionInstanceData*>(InDataFromGameThread);
		*DataForRenderThread = *DataFromGameThread;
	}

    //加入线程数据
	virtual void ConsumePerInstanceDataFromGameThread(void* PerInstanceData, const FNiagaraSystemInstanceID& InstanceID) override
	{
		FNDIMousePositionInstanceData* InstanceDataFromGT = static_cast<FNDIMousePositionInstanceData*>(PerInstanceData);
		FNDIMousePositionInstanceData& InstanceData = SystemInstancesToInstanceData_RT.FindOrAdd(InstanceID);
		InstanceData = *InstanceDataFromGT;

		// we call the destructor here to clean up the GT data. Without this we could be leaking memory.
		InstanceDataFromGT->~FNDIMousePositionInstanceData();
	}

	TMap<FNiagaraSystemInstanceID, FNDIMousePositionInstanceData> SystemInstancesToInstanceData_RT;
};
```
```c++ NiagaraDataInterfaceMousePosition
class UNiagaraDataInterfaceMousePosition : public UNiagaraDataInterface
{
	GENERATED_UCLASS_BODY()
//传入GPu参数结构体
	BEGIN_SHADER_PARAMETER_STRUCT(FShaderParameters, )
		SHADER_PARAMETER(FVector4f,				MousePosition)
	END_SHADER_PARAMETER_STRUCT()

public:
	//UObject Interface
	virtual void PostInitProperties() override;
	//UObject Interface End

	//UNiagaraDataInterface Interface
	
	//新建function，GPu和CPu
	virtual void GetFunctions(TArray<FNiagaraFunctionSignature>& OutFunctions) override;
	
	//CPU Function生成 绑定lambda
	virtual void GetVMExternalFunction(const FVMExternalFunctionBindingInfo& BindingInfo, void* InstanceData, FVMExternalFunction &OutFunc) override;
	virtual bool CanExecuteOnTarget(ENiagaraSimTarget Target) const override { return true; }
#if WITH_EDITORONLY_DATA
    
    //让niagara编译知道要那些文件
	virtual bool AppendCompileHash(FNiagaraCompileHashVisitor* InVisitor) const override;
	
	//生成gpu 函数，要是Datainstance只支持cpu可以不要这个
	virtual bool GetFunctionHLSL(const FNiagaraDataInterfaceGPUParamInfo& ParamInfo, const FNiagaraDataInterfaceGeneratedFunction& FunctionInfo, int FunctionInstanceIndex, FString& OutHLSL) override;
	
	//绑定hlsl文件路径 include
	virtual void GetParameterDefinitionHLSL(const FNiagaraDataInterfaceGPUParamInfo& ParamInfo, FString& OutHLSL) override;
#endif
	virtual bool UseLegacyShaderBindings() const override { return false; }
	
	//把shaderparameter加入到构建里面
	virtual void BuildShaderParameters(FNiagaraShaderParametersBuilder& ShaderParametersBuilder) const override;
	
	//传shaderparameter到GPu里
	virtual void SetShaderParameters(const FNiagaraDataInterfaceSetShaderParametersContext& Context) const override;

    //创立一个新object去存数据
	virtual bool InitPerInstanceData(void* PerInstanceData, FNiagaraSystemInstance* SystemInstance) override;
	virtual void DestroyPerInstanceData(void* PerInstanceData, FNiagaraSystemInstance* SystemInstance) override;
	
	//开辟内存
	virtual int32 PerInstanceDataSize() const override;
	virtual bool HasPreSimulateTick() const override { return true; }
	//每个instance前要传的数据
	virtual bool PerInstanceTick(void* PerInstanceData, FNiagaraSystemInstance* SystemInstance, float DeltaSeconds) override;
	virtual void ProvidePerInstanceDataForRenderThread(void* DataForRenderThread, void* PerInstanceData, const FNiagaraSystemInstanceID& SystemInstance) override;
	//UNiagaraDataInterface Interface

	void GetMousePositionVM(FVectorVMExternalFunctionContext& Context);	
private:
	static const FName GetMousePositionName;
};
```