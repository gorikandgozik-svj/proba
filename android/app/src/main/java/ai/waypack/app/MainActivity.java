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
import android.content.res.AssetFileDescriptor;
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
    private static final ExecutorService worker = Executors.newSingleThreadExecutor();
    private static boolean libraryAvailable;
    static {
        try { System.loadLibrary("waypack-ai"); libraryAvailable = true; }
        catch (Throwable err) { libraryAvailable = false; }
    }
    private static native String inferLocal(String modelPath, String prompt);
    private volatile boolean modelReady = false;
    private final java.util.concurrent.atomic.AtomicInteger requestSerial=new java.util.concurrent.atomic.AtomicInteger();
    private File modelFile;
    private WebView view;
    private String textToSave = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(21,32,61));
        getWindow().setNavigationBarColor(Color.rgb(21,32,61));
        TextView splash = new TextView(this);
        splash.setText("✦ WAYPACK AI\n\nПодготавливаем быструю Gemma 3...\n\nЭто требуется только при первом запуске.");
        splash.setTextColor(Color.rgb(25,34,61));
        splash.setBackgroundColor(Color.rgb(246,247,251));
        splash.setGravity(Gravity.CENTER);
        splash.setTextSize(19);
        splash.setPadding(32,32,32,32);
        setContentView(splash);
        worker.execute(() -> {
            try {
                if (libraryAvailable) {
                    modelFile = prepareModel();
                    modelReady = modelFile != null && modelFile.isFile();
                }
            } catch (Exception ex) {
                android.util.Log.e("WAYPACK","Failed preparing local model",ex);
                modelReady = false;
            }
            runOnUiThread(this::showWebApp);
        });
    }

    private File prepareModel() throws IOException {
        File target = new File(getFilesDir(),"gemma3-270m-q4.gguf");
        long expected;
        try (AssetFileDescriptor fd = getAssets().openFd("model.gguf")) { expected = fd.getLength(); }
        if (expected < 100_000_000L) throw new IOException("Model weight file missing or truncated");
        if (target.isFile() && target.length()==expected) return target;
        File partial = new File(getFilesDir(),"gemma3-270m-q4.partial");
        try (InputStream in=new BufferedInputStream(getAssets().open("model.gguf",android.content.res.AssetManager.ACCESS_STREAMING),1024*1024);
             OutputStream out=new BufferedOutputStream(new FileOutputStream(partial),1024*1024)) {
            byte[] block=new byte[1024*1024];
            int count;
            while ((count=in.read(block))!=-1) out.write(block,0,count);
            out.flush();
        }
        if (partial.length()!=expected) {partial.delete();throw new IOException("Model copying incomplete");}
        if (target.exists() && !target.delete()) throw new IOException("Cannot replace old model");
        if (!partial.renameTo(target)) throw new IOException("Cannot commit local model");
        return target;
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
                if(!"https".equals(uri.getScheme()) || !APP_HOST.equals(uri.getHost())) return null;
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
    private String makePrompt(JSONObject data, java.util.List<JSONObject> choices) throws Exception {
        JSONObject p=data.getJSONObject("profile");
        StringBuilder b=new StringBuilder(950);
        b.append("<start_of_turn>user\n");
        b.append("Выбери ТРИ самых полезных предмета из списка для поездки. ");
        b.append("Предметы уже проверены: их нет в чемодане. ");
        b.append("Ответь только ТРЕМЯ разными номерами через запятую, например 2,4,1. Без слов.\n");
        b.append("Направление: ").append(clipped(p.optString("country"),35)).append(", ")
            .append(clipped(p.optString("city"),35)).append(". ");
        b.append("Дней: ").append(Math.max(1,Math.min(60,p.optInt("days",7)))).append(". ");
        b.append("Дата: ").append(clipped(p.optString("date"),10)).append(". ");
        JSONArray acts=data.optJSONArray("activities");
        if(acts!=null){
            b.append("Занятия: ");
            for(int i=0;i<Math.min(acts.length(),5);i++)b.append(clipped(acts.optString(i),18)).append(", ");
        }
        b.append("\nВАРИАНТЫ:\n");
        for(int i=0;i<choices.size();i++)b.append(i+1).append(". ").append(choices.get(i).optString("name")).append("\n");
        b.append("Три номера: <end_of_turn>\n<start_of_turn>model\n");
        return b.toString();
    }
    private JSONObject selectedRecommendations(String generated, java.util.List<JSONObject> choices) throws Exception {
        if(generated==null || generated.startsWith("ERROR:"))generated="";
        JSONArray items=new JSONArray();
        java.util.HashSet<Integer> seen=new java.util.HashSet<>();
        String clean=generated.trim();
        boolean obeyedFormat=clean.matches("[1-9]\\s*[,;]\\s*[1-9]\\s*[,;]\\s*[1-9]");
        java.util.regex.Matcher m=java.util.regex.Pattern.compile("[1-9]").matcher(obeyedFormat?clean:"");
        int aiSelections=0;
        while(m.find() && items.length()<3){
            int n=Integer.parseInt(m.group())-1;
            if(n<0||n>=choices.size()||!seen.add(n))continue;
            JSONObject c=choices.get(n);
            items.put(new JSONObject()
                .put("name",c.getString("name")).put("qty",1)
                .put("category",c.getString("category"))
                .put("reason","Выбрано Gemma · "+c.getString("reason")));
            aiSelections++;
        }
        // Explicitly identified rule-based fallback when the small LLM ignores number format.
        for(int n=0;n<choices.size()&&items.length()<3;n++){
            if(!seen.add(n))continue;
            JSONObject c=choices.get(n);
            items.put(new JSONObject()
                .put("name",c.getString("name")).put("qty",1)
                .put("category",c.getString("category"))
                .put("reason","Подобрано правилами · "+c.getString("reason")));
        }
        return new JSONObject().put("items",items)
            .put("model","Gemma 3 270M · быстрый подбор")
            .put("realModel",aiSelections>0)
            .put("selectedByAI",aiSelections);
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
        @JavascriptInterface public boolean isModelReady() {return modelReady;}
        @JavascriptInterface public void runModel(String id,String payload) {
            if (id==null || id.length()>80 || payload==null || payload.length()>16000) return;
            if (!modelReady || modelFile==null) {
                deliver(id,503,"{\"error\":\"Модель Gemma не загружена\"}");
                return;
            }
            final int serial=requestSerial.incrementAndGet();
            worker.execute(() -> {
                if(serial!=requestSerial.get())return;
                try {
                    JSONObject data=new JSONObject(payload);
                    JSONObject profile=data.optJSONObject("profile");
                    if(profile==null || !data.has("activities"))throw new IOException("Некорректные данные поездки");
                    java.util.ArrayList<JSONObject> pool=vettedCandidates(data);
                    if(pool.size()>9)pool=new java.util.ArrayList<>(pool.subList(0,9));
                    JSONObject ready;
                    if(pool.isEmpty()){
                        ready=new JSONObject().put("items",new JSONArray())
                            .put("model","Gemma 3 270M").put("realModel",false);
                    } else {
                        String generated=inferLocal(modelFile.getAbsolutePath(),makePrompt(data,pool));
                        ready=selectedRecommendations(generated,pool);
                    }
                    if(serial==requestSerial.get())deliver(id,200,ready.toString());
                } catch(Throwable e) {
                    String msg=e.getMessage()==null?"Ошибка Gemma":e.getMessage();
                    if(serial==requestSerial.get())deliver(id,502,"{\"error\":"+JSONObject.quote(msg.substring(0,Math.min(msg.length(),140)))+"}");
                }
            });
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
        if(view!=null){view.removeJavascriptInterface("WaypackNative");view.destroy();view=null;}
        super.onDestroy();
    }
}
