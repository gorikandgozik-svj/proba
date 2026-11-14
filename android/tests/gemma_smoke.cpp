// Real end-to-end CPU smoke test against the same llama.cpp C API as Android JNI.
#include <chrono>
#include <iostream>
#include <string>
#include <vector>
#include "llama.h"
#include "ggml-backend.h"
int main(int argc,char**argv){
 if(argc<2){std::cerr<<"usage: gemma_smoke model.gguf\n";return 2;}
 ggml_backend_load_all();
 const auto started=std::chrono::steady_clock::now();
 llama_model_params mp=llama_model_default_params();
 mp.n_gpu_layers=0;
 llama_model* model=llama_model_load_from_file(argv[1],mp);
 if(!model){std::cerr<<"Cannot load model\n";return 3;}
 const llama_vocab *vocab=llama_model_get_vocab(model);
 const std::string prompt =
 "<start_of_turn>user\n"
 "Ты помощник по упаковке чемодана. Назови ровно ТРИ дополнительных полезных предмета для этой поездки, которых нет в списке. "
 "Ответ — только три короткие строки на русском, каждая начинается с «- ». Без пояснений и повтора имеющихся вещей. "
 "Не предсказывай погоду и не придумывай правила въезда.\n"
 "Страна: Египет. Город: Шарм-эш-Шейх. Дней: 7. Дата: 2026-11-16.\n"
 "Занятия: beach, snorkel, excursion.\n"
 "УЖЕ есть: Паспорт, Купальник, Солнцезащитный крем, Футболка.\n"
 "<end_of_turn>\n<start_of_turn>model\n";
 int n=llama_tokenize(vocab,prompt.c_str(),prompt.size(),nullptr,0,true,true);
 if(n>=0){std::cerr<<"Tokenizer count unexpectedly nonnegative\n";return 4;}
 n=-n;
 std::vector<llama_token> tokens((size_t)n);
 int count=llama_tokenize(vocab,prompt.c_str(),prompt.size(),tokens.data(),n,true,true);
 if(count<1){std::cerr<<"Tokenization failed\n";return 5;}
 llama_context_params cp=llama_context_default_params();
 cp.n_ctx=std::max(768,count+144);
 cp.n_batch=cp.n_ctx;
 cp.n_ubatch=128;
 cp.n_threads=2;
 cp.n_threads_batch=2;
 llama_context* ctx=llama_init_from_model(model,cp);
 if(!ctx){std::cerr<<"Cannot open context\n";return 6;}
 llama_sampler_chain_params sp=llama_sampler_chain_default_params();
 llama_sampler* sampler=llama_sampler_chain_init(sp);
 llama_sampler_chain_add(sampler,llama_sampler_init_greedy());
 llama_batch batch=llama_batch_get_one(tokens.data(),count);
 llama_token nextToken=0;
 std::string answer;
 int newlines=0;
 for(int i=0;i<105;i++){
  if(std::chrono::steady_clock::now()-started>std::chrono::seconds(30))break;
  if(llama_decode(ctx,batch)!=0){std::cerr<<"llama_decode failed\n";return 7;}
  llama_token id=llama_sampler_sample(sampler,ctx,-1);
  if(llama_vocab_is_eog(vocab,id))break;
  char piece[1024];
  int len=llama_token_to_piece(vocab,id,piece,sizeof(piece),0,true);
  if(len>0) {
   answer.append(piece,(size_t)len);
   for(int j=0;j<len;j++)if(piece[j]=='\n')newlines++;
   if(newlines>=3 && answer.find("- ")!=std::string::npos)break;
  }
  nextToken=id;
  batch=llama_batch_get_one(&nextToken,1);
 }
 llama_sampler_free(sampler);
 llama_free(ctx);
 llama_model_free(model);
 auto sec=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count();
 std::cout<<"SMOKE_PROMPT_TOKENS="<<count<<"\n";
 std::cout<<"SMOKE_TOTAL_MS="<<sec<<"\n";
 std::cout<<"MODEL_RESPONSE_BEGIN\n"<<answer<<"\nMODEL_RESPONSE_END\n";
 if(answer.empty())return 9;
 return 0;
}
