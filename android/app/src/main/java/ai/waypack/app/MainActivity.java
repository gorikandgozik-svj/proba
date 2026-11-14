package ai.waypack.app;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.content.ActivityNotFoundException;
import android.graphics.Color;
import android.net.Uri;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.Toast;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import com.google.ai.edge.litert.Accelerator;
import com.google.ai.edge.litert.CompiledModel;
import com.google.ai.edge.litert.TensorBuffer;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String APP_HOST = "appassets.androidplatform.net";
    private static final String APP_URL = "https://" + APP_HOST + "/index.html";
    private static final int SAVE_TEXT = 420;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private volatile boolean modelReady=false;
    private final java.util.concurrent.atomic.AtomicInteger requestSerial=new java.util.concurrent.atomic.AtomicInteger();
    private CompiledModel rankerModel;
    private List<TensorBuffer> rankerInput;
    private List<TensorBuffer> rankerOutput;
    private WebView view;
    private String textToSave = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(21,32,61));
        getWindow().setNavigationBarColor(Color.rgb(21,32,61));
        // Render the complete deterministic app without waiting for ML runtime.
        showWebApp();
        worker.execute(() -> {
            try {
                rankerModel=CompiledModel.create(
                    getAssets(),"waypack-ranker.tflite",new CompiledModel.Options(Accelerator.CPU));
                rankerInput=rankerModel.createInputBuffers();
                rankerOutput=rankerModel.createOutputBuffers();
                if(rankerInput.size()!=1||rankerOutput.size()!=1)
                    throw new IllegalStateException("Unexpected LiteRT tensor count");
                modelReady=true;
            }catch(Throwable err){
                modelReady=false;
                android.util.Log.w("WAYPACK","Google LiteRT initialization failed, safe fallback enabled",err);
            }
            if(modelReady)runOnUiThread(() -> {
                if(view!=null&&!isFinishing()&&!isDestroyed())
                    view.evaluateJavascript("window.waypackModelReady&&window.waypackModelReady()",null);
            });
        });
    }

    private void showWebApp() {
        if (isFinishing() || isDestroyed()) return;
        view = new WebView(this);
        view.setBackgroundColor(Color.rgb(246,247,251));
        WebView.setWebContentsDebuggingEnabled(false);
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        view.addJavascriptInterface(new NativeBridge(),"WaypackNative");
        view.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView webView, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if(!"https".equals(uri.getScheme()) || !APP_HOST.equals(uri.getHost())) return missing();
                String file=uri.getPath();
                if (!"/index.html".equals(file) && !"/".equals(file)) return missing();
                try {
                    InputStream is=getAssets().open("index.html");
                    return new WebResourceResponse("text/html","UTF-8",is);
                } catch(Exception e) {return missing();}
            }
            @Override public boolean shouldOverrideUrlLoading(WebView webView,WebResourceRequest request) {
                Uri uri=request.getUrl();
                if("https".equals(uri.getScheme()) && APP_HOST.equals(uri.getHost()) && "/index.html".equals(uri.getPath()))return false;
                if(request.isForMainFrame() && ("https".equals(uri.getScheme()) || "mailto".equals(uri.getScheme()))) {
                    try {startActivity(new Intent(Intent.ACTION_VIEW,uri));}
                    catch(ActivityNotFoundException ignored){}
                }
                return true;
            }
        });
        setContentView(view);
        view.loadUrl(APP_URL);
    }
    private WebResourceResponse missing() {
        return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",
            Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
    }
    private void deliver(String id,int code,String json) {
        runOnUiThread(() -> {
            if (view != null) {
                String script="window.waypackNativeResolve&&window.waypackNativeResolve(" +
                    JSONObject.quote(id)+","+JSONObject.quote(json)+","+code+")";
                view.evaluateJavascript(script,null);
            }
        });
    }
    private static String clipped(String input,int max){
        if(input==null)return "";
        String value=input.replaceAll("[\\r\\n\\t]"," ").trim();
        return value.substring(0,Math.min(value.length(),max));
    }

    // Compact vetted candidate pool: no fabricated travel rules and no repeated packed items.
    private static String normalized(String str) {
        return (str == null ? "" : str.toLowerCase(java.util.Locale.ROOT)
            .replace('ё','е').replaceAll("[^a-zа-я0-9]+"," ").trim());
    }
    private static void addCandidate(java.util.List<JSONObject> pool, java.util.Set<String> already,
                                      String name, String category, String reason) throws Exception {
        String key=normalized(name);
        if(key.isEmpty())return;
        for(String packed:already){
            if(packed.equals(key) || (packed.length()>9 && (packed.contains(key) || key.contains(packed))))return;
        }
        for(JSONObject c:pool) if(normalized(c.optString("name")).equals(key)) return;
        pool.add(new JSONObject().put("name",name).put("category",category).put("reason",reason));
    }
    private java.util.ArrayList<JSONObject> vettedCandidates(JSONObject data) throws Exception {
        java.util.HashSet<String> packed=new java.util.HashSet<>();
        JSONArray existing=data.optJSONArray("currentItems");
        if(existing!=null)for(int i=0;i<existing.length();i++){
            JSONObject e=existing.optJSONObject(i);
            if(e!=null)packed.add(normalized(e.optString("name")));
        }
        java.util.ArrayList<JSONObject> result=new java.util.ArrayList<>();
        java.util.HashSet<String> activities=new java.util.HashSet<>();
        JSONArray acts=data.optJSONArray("activities");
        if(acts!=null)for(int i=0;i<Math.min(acts.length(),22);i++)activities.add(acts.optString(i));
        if(activities.contains("beach")||activities.contains("snorkel")||activities.contains("diving")||activities.contains("boat")||activities.contains("surf")){
            addCandidate(result,packed,"Гермомешок для телефона","activity","Защита электроники от брызг");
            addCandidate(result,packed,"Полотенце из микрофибры","hygiene","Компактно для пляжа");
            addCandidate(result,packed,"Прищепки для пляжного полотенца","activity","Полотенце не унесёт ветром");
            addCandidate(result,packed,"Складная пляжная сумка","other","Удобно брать вещи к морю");
            addCandidate(result,packed,"Мешочек для мокрых вещей","hygiene","Не намочит остальной багаж");
        }
        if(activities.contains("hiking")||activities.contains("camping")||activities.contains("parkour")){
            addCandidate(result,packed,"Налобный фонарь","activity","Освобождает руки в темноте");
            addCandidate(result,packed,"Плащ-дождевик","clothes","На случай осадков");
            addCandidate(result,packed,"Пластыри от мозолей","hygiene","Для долгих прогулок");
            addCandidate(result,packed,"Чехол от дождя на рюкзак","activity","Сохранит вещи сухими");
        }
        if(activities.contains("ski")||activities.contains("snowboard")){
            addCandidate(result,packed,"Бафф для шеи","clothes","Закрывает шею от ветра");
            addCandidate(result,packed,"Грелки для рук","activity","Полезны на морозе");
            addCandidate(result,packed,"Салфетка для горнолыжной маски","activity","Для ухода за линзой");
        }
        if(activities.contains("photo")||activities.contains("video")){
            addCandidate(result,packed,"Салфетка для объектива","tech","Чтобы бережно очищать оптику");
            addCandidate(result,packed,"Запасная карта памяти","tech","Резерв для снимков");
            addCandidate(result,packed,"Мешочек для кабелей","tech","Мелкие аксессуары не потеряются");
        }
        addCandidate(result,packed,"Бирка с контактом на багаж","documents","Для идентификации чемодана");
        addCandidate(result,packed,"Мешок для грязной одежды","other","Отделить использованные вещи");
        addCandidate(result,packed,"Небольшой дорожный органайзер","other","Удобно разместить мелочи");
        addCandidate(result,packed,"Пакеты с застёжкой","hygiene","Защитить вещи от протечек");
        addCandidate(result,packed,"Складная сумка для покупок","other","Не занимает много места");
        addCandidate(result,packed,"Мини-набор для шитья","other","Для мелкого ремонта одежды");
        addCandidate(result,packed,"Беруши для сна","hygiene","Для отдыха в шумной обстановке");
        addCandidate(result,packed,"Компактные влажные салфетки","hygiene","Для рук в дороге");
        return result;
    }

    // 18 float features, exact schema shared with tools/train_waypack_ranker.py.
    // Tags: beach, hiking, winter sports, photo/video, universal travel.
    private static float[] features(JSONObject data,JSONObject item){
        float[] f=new float[18];
        String name=normalized(item.optString("name"));
        int tag=4;
        if(name.contains("гермомеш")||name.contains("микрофибр")||name.contains("пляж")||name.contains("мокрых"))tag=0;
        else if(name.contains("налобн")||name.contains("дождевик")||name.contains("мозол")||name.contains("рюкзак"))tag=1;
        else if(name.contains("бафф")||name.contains("грелк")||name.contains("горнолыж"))tag=2;
        else if(name.contains("объектив")||name.contains("карт")&&name.contains("памят")||name.contains("кабел"))tag=3;
        f[tag]=1f;
        JSONArray acts=data.optJSONArray("activities");
        if(acts!=null)for(int i=0;i<Math.min(acts.length(),22);i++){
            String act=acts.optString(i);
            if("beach".equals(act)||"snorkel".equals(act)||"diving".equals(act)||"boat".equals(act)||"surf".equals(act))f[5]=1f;
            if("hiking".equals(act)||"camping".equals(act)||"parkour".equals(act))f[6]=1f;
            if("ski".equals(act)||"snowboard".equals(act))f[7]=1f;
            if("photo".equals(act)||"video".equals(act))f[8]=1f;
        }
        JSONObject p=data.optJSONObject("profile");
        if(p==null)p=new JSONObject();
        String date=p.optString("date","");
        int month=0;
        if(date.length()>=7)try{month=Integer.parseInt(date.substring(5,7));}catch(NumberFormatException ignored){}
        String country=normalized(p.optString("country"));
        boolean coldPlace=country.contains("норвег")||country.contains("финлянд")||country.contains("швец")||
            country.contains("исланд")||country.contains("швейцар")||country.contains("канад")||country.contains("росси");
        boolean hotPlace=country.contains("египет")||country.contains("таиланд")||country.contains("оаэ")||
            country.contains("индонез")||country.contains("мальдив")||country.contains("турци");
        f[9]=(f[7]>0||(coldPlace&&(month==12||month==1||month==2)))?1f:0f;
        f[10]=(f[5]>0&&hotPlace)?1f:0f;
        f[11]=Math.min(1f,Math.max(1,p.optInt("days",7))/30f);
        f[12]=Math.min(1f,Math.max(1,p.optInt("people",1))/8f);
        f[13]="cabin".equals(p.optString("luggage"))?1f:0f;
        f[14]="documents".equals(item.optString("category"))?0.85f:
              "hygiene".equals(item.optString("category"))?0.68f:
              "tech".equals(item.optString("category"))?0.64f:0.56f;
        if(name.contains("гермомеш")||name.contains("пластыри"))f[14]=0.88f;
        f[15]=p.optInt("laundry",0)>0?1f:0f;
        f[16]=(name.contains("мокрых")||name.contains("гермомеш")||name.contains("пакеты"))?1f:0f;
        f[17]=("tech".equals(item.optString("category"))||name.contains("телефон"))?1f:0f;
        return f;
    }

    // Never runs on the main/UI thread. Google LiteRT CPU interpreter is
    // initialized once; buffers are reused for all candidates.
    private JSONObject neuralRecommendations(JSONObject data,java.util.List<JSONObject> choices) throws Exception {
        if(!modelReady||rankerModel==null||rankerInput==null||rankerOutput==null)throw new IllegalStateException("Google LiteRT not ready");
        java.util.ArrayList<Integer> indices=new java.util.ArrayList<>();
        java.util.HashMap<Integer,Float> scores=new java.util.HashMap<>();
        for(int i=0;i<choices.size();i++){
            float[] input=features(data,choices.get(i));
            rankerInput.get(0).writeFloat(input);
            rankerModel.run(rankerInput,rankerOutput);
            float score=rankerOutput.get(0).readFloat()[0];
            if(!Float.isFinite(score))throw new IOException("Nonfinite neural score");
            scores.put(i,score);
            indices.add(i);
        }
        indices.sort((x,y)->Float.compare(scores.get(y),scores.get(x)));
        JSONArray items=new JSONArray();
        for(int i=0;i<Math.min(3,indices.size());i++){
            int idx=indices.get(i);
            JSONObject c=choices.get(idx);
            items.put(new JSONObject()
               .put("name",c.optString("name")).put("qty",1)
               .put("category",c.optString("category"))
               .put("reason","Подбор Google LiteRT RankNet · "+c.optString("reason")));
        }
        return new JSONObject().put("items",items)
          .put("model","Google LiteRT · WAYPACK RankNet")
          .put("realModel",true).put("selectedByAI",items.length())
          .put("modelKind","task-specific-18d-ranker");
    }

    private JSONObject selectedRecommendations(String ignored, java.util.List<JSONObject> choices) throws Exception {
        JSONArray items=new JSONArray();
        for(int i=0;i<Math.min(3,choices.size());i++){
            JSONObject c=choices.get(i);
            items.put(new JSONObject().put("name",c.optString("name"))
              .put("qty",1).put("category",c.optString("category"))
              .put("reason","Быстрый подбор · "+c.optString("reason")));
        }
        return new JSONObject().put("items",items)
          .put("model","WAYPACK Fast Engine").put("realModel",false).put("selectedByAI",0);
    }

    public final class NativeBridge {
        @JavascriptInterface public void haptic() {
            runOnUiThread(() -> {
                try {
                    android.os.Vibrator v=(android.os.Vibrator)getSystemService(VIBRATOR_SERVICE);
                    if(v!=null && v.hasVibrator()){
                        if(android.os.Build.VERSION.SDK_INT>=29) v.vibrate(android.os.VibrationEffect.createPredefined(android.os.VibrationEffect.EFFECT_TICK));
                        else v.vibrate(android.os.VibrationEffect.createOneShot(12,android.os.VibrationEffect.DEFAULT_AMPLITUDE));
                    }
                }catch(Exception ignored){}
            });
        }
        @JavascriptInterface public boolean isModelReady(){return true;}
        @JavascriptInterface public boolean isNeuralReady(){return modelReady;}

        @JavascriptInterface public void runModel(String id,String payload){
            if(id==null||id.length()>80)return;
            if(payload==null||payload.length()>16000){
                deliver(id,400,"{\"error\":\"Некорректный запрос\"}");return;
            }
            final int serial=requestSerial.incrementAndGet();
            try{
                JSONObject data=new JSONObject(payload);
                if(data.optJSONObject("profile")==null||data.optJSONArray("activities")==null)
                    throw new IOException("Недостаточно данных поездки");
                java.util.ArrayList<JSONObject> pool=vettedCandidates(data);
                if(pool.size()>9)pool=new java.util.ArrayList<>(pool.subList(0,9));
                final java.util.ArrayList<JSONObject> choices=pool;
                JSONObject instant=selectedRecommendations("",choices);
                instant.put("model","WAYPACK Fast Engine");
                instant.put("neuralPending",modelReady&&!choices.isEmpty());
                // Return BEFORE any LiteRT inference, so slow devices never hang.
                deliver(id,200,instant.toString());

                if(!choices.isEmpty()){
                    worker.execute(()->{
                        if(serial!=requestSerial.get()||!modelReady)return;
                        try{
                            JSONObject enriched=neuralRecommendations(data,choices);
                            if(serial!=requestSerial.get())return;
                            final String json=enriched.toString();
                            runOnUiThread(()->{
                                if(serial==requestSerial.get()&&view!=null&&!isFinishing()&&!isDestroyed()){
                                    view.evaluateJavascript(
                                        "window.waypackNativeEnhance&&window.waypackNativeEnhance("+
                                        JSONObject.quote(id)+","+JSONObject.quote(json)+")",null);
                                }
                            });
                        }catch(Throwable err){
                            android.util.Log.w("WAYPACK","Optional LiteRT ranking failed",err);
                        }
                    });
                }
            }catch(Throwable err){
                String message=err.getMessage()==null?"Некорректные данные":err.getMessage();
                deliver(id,400,"{\"error\":"+JSONObject.quote(message.substring(0,Math.min(message.length(),120)))+"}");
            }
        }
        @JavascriptInterface public void shareText(String raw) {
            if (raw==null)return;
            final String txt=raw.substring(0,Math.min(raw.length(),300000));
            runOnUiThread(() -> {
                Intent share=new Intent(Intent.ACTION_SEND);
                share.setType("text/plain");
                share.putExtra(Intent.EXTRA_SUBJECT,"WAYPACK AI — мой чемодан");
                share.putExtra(Intent.EXTRA_TEXT,txt);
                try {startActivity(Intent.createChooser(share,"Поделиться списком"));}
                catch(ActivityNotFoundException ignored){}
            });
        }
        @JavascriptInterface public void saveText(String raw) {
            if(raw==null)return;
            final String txt=raw.substring(0,Math.min(raw.length(),300000));
            runOnUiThread(() -> {
                textToSave=txt;
                Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);
                save.addCategory(Intent.CATEGORY_OPENABLE);
                save.setType("text/plain");
                save.putExtra(Intent.EXTRA_TITLE,"waypack-list.txt");
                try {startActivityForResult(save,SAVE_TEXT);}
                catch(ActivityNotFoundException ignored){}
            });
        }
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode!=SAVE_TEXT || resultCode!=RESULT_OK || data==null || data.getData()==null)return;
        try(OutputStream out=getContentResolver().openOutputStream(data.getData())){
            if(out!=null)out.write(("\uFEFF"+textToSave).getBytes(StandardCharsets.UTF_8));
        }catch(Exception e){Toast.makeText(this,"Не удалось сохранить файл",Toast.LENGTH_LONG).show();}
        finally{textToSave="";}
    }
    @Override public void onBackPressed(){
        if(view==null){super.onBackPressed();return;}
        view.evaluateJavascript("Boolean(window.waypackGoBack && window.waypackGoBack())",v->{
            if(!"true".equals(v))MainActivity.super.onBackPressed();
        });
    }
    @Override protected void onDestroy(){
        requestSerial.incrementAndGet();
        if(view!=null){view.removeJavascriptInterface("WaypackNative");view.destroy();view=null;}
        worker.execute(() -> {
            try {
                if(rankerInput!=null)for(TensorBuffer b:rankerInput)b.close();
                if(rankerOutput!=null)for(TensorBuffer b:rankerOutput)b.close();
                if(rankerModel!=null)rankerModel.close();
            }catch(Exception ignored){}
        });
        worker.shutdown();
        super.onDestroy();
    }
}
