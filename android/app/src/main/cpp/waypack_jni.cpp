#include <jni.h>
#include <android/log.h>
#include <algorithm>
#include <mutex>
#include <thread>
#include <string>
#include <vector>
#include "llama.h"
#include "ggml-backend.h"

static std::mutex guard;
static llama_model * loadedModel = nullptr;
static std::string loadedPath;
static std::string fromJava(JNIEnv * env, jstring str) {
    if (!str) return {};
    const char * utf = env->GetStringUTFChars(str, nullptr);
    if (!utf) return {};
    std::string out(utf);
    env->ReleaseStringUTFChars(str, utf);
    return out;
}
static jstring result(JNIEnv *env, const std::string &txt) { return env->NewStringUTF(txt.c_str()); }
static void logMsg(const std::string &msg) { __android_log_print(ANDROID_LOG_INFO,"WAYPACK-QWEN","%s",msg.c_str()); }
extern "C" JNIEXPORT jstring JNICALL
Java_ai_waypack_app_MainActivity_inferLocal(JNIEnv *env, jclass, jstring jpath, jstring jprompt) {
    std::lock_guard<std::mutex> lock(guard);
    const std::string path = fromJava(env,jpath);
    const std::string prompt = fromJava(env,jprompt);
    if(path.empty()||prompt.empty()) return result(env,"ERROR:empty model or prompt");
    ggml_backend_load_all();
    if(!loadedModel || path != loadedPath){
        if (loadedModel) {llama_model_free(loadedModel);loadedModel=nullptr;}
        llama_model_params mp=llama_model_default_params();
        mp.n_gpu_layers=0; mp.use_mmap=true;
        loadedModel=llama_model_load_from_file(path.c_str(),mp);
        if(!loadedModel)return result(env,"ERROR:model load failed");
        loadedPath=path;
        logMsg("GGUF model loaded");
    }
    const llama_vocab *vocab=llama_model_get_vocab(loadedModel);
    if(!vocab)return result(env,"ERROR:vocab unavailable");
    int n=llama_tokenize(vocab,prompt.c_str(),prompt.size(),nullptr,0,true,true);
    if(n>=0)return result(env,"ERROR:unexpected token count");
    n=-n;
    if(n<1||n>2600)return result(env,"ERROR:prompt too long");
    std::vector<llama_token> tok(static_cast<size_t>(n));
    int actual=llama_tokenize(vocab,prompt.c_str(),prompt.size(),tok.data(),n,true,true);
    if(actual<1)return result(env,"ERROR:tokenizer failed");
    llama_context_params cp=llama_context_default_params();
    cp.n_ctx=std::max(2048,actual+480);
    cp.n_batch=cp.n_ctx;
    cp.n_threads=std::min(4, std::max(2,(int)std::thread::hardware_concurrency()));
    cp.n_threads_batch=cp.n_threads;
    llama_context * ctx=llama_init_from_model(loadedModel,cp);
    if(!ctx)return result(env,"ERROR:context init failed");
    llama_sampler_chain_params sp=llama_sampler_chain_default_params();
    llama_sampler * sampler=llama_sampler_chain_init(sp);
    llama_sampler_chain_add(sampler,llama_sampler_init_greedy());
    llama_batch batch=llama_batch_get_one(tok.data(),actual);
    std::string text;
    llama_token id=0;
    for(int i=0;i<370;i++){
        if(llama_decode(ctx,batch)!=0){text="ERROR:decode failed";break;}
        id=llama_sampler_sample(sampler,ctx,-1);
        if(llama_vocab_is_eog(vocab,id))break;
        char piece[1024];int len=llama_token_to_piece(vocab,id,piece,sizeof(piece),0,true);
        if(len>0) text.append(piece,static_cast<size_t>(len));
        batch=llama_batch_get_one(&id,1);
    }
    llama_sampler_free(sampler);
    llama_free(ctx);
    if(text.size()>20000)text.resize(20000);
    logMsg("Inference completed, output bytes="+std::to_string(text.size()));
    return result(env,text);
}
