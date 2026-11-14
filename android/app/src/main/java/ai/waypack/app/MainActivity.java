package ai.waypack.app;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.content.ActivityNotFoundException;
import android.graphics.Color;
import android.net.Uri;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;

/**
 * A standalone offline-first Android shell: all executable HTML/JS is packaged
 * inside the signed APK. No accounts, permissions, or secrets are required.
 * Remote AI is optional and may be enabled only by an HTTPS backend.
 */
public final class MainActivity extends Activity {
  private static final String APP_HOST = "appassets.androidplatform.net";
  private static final String APP_URL = "https://" + APP_HOST + "/index.html";
  private static final int SAVE_TEXT = 420;
  private WebView view;
  private String textToSave = "";

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(Color.rgb(21, 32, 61));
    getWindow().setNavigationBarColor(Color.rgb(21, 32, 61));
    view = new WebView(this);
    view.setBackgroundColor(Color.rgb(246, 247, 251));
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
    view.addJavascriptInterface(new NativeBridge(), "WaypackNative");
    view.setWebViewClient(new WebViewClient() {
      @Override public WebResourceResponse shouldInterceptRequest(WebView webView, WebResourceRequest request) {
        Uri uri = request.getUrl();
        if (!"https".equals(uri.getScheme()) || !APP_HOST.equals(uri.getHost())) return null;
        String file = uri.getPath();
        if (!"/index.html".equals(file) && !"/".equals(file)) return missing();
        try {
          InputStream is = getAssets().open("index.html");
          return new WebResourceResponse("text/html", "UTF-8", is);
        } catch(Exception e) { return missing(); }
      }
      @Override public boolean shouldOverrideUrlLoading(WebView webView, WebResourceRequest request) {
        Uri uri = request.getUrl();
        if ("https".equals(uri.getScheme()) && APP_HOST.equals(uri.getHost()) && "/index.html".equals(uri.getPath())) return false;
        if (request.isForMainFrame() && ("https".equals(uri.getScheme()) || "mailto".equals(uri.getScheme()))) {
          try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); }
          catch (ActivityNotFoundException ignored) {}
        }
        return true;
      }
    });
    setContentView(view);
    view.loadUrl(APP_URL);
  }

  private WebResourceResponse missing() {
    return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found",
      Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
  }

  public final class NativeBridge {
    @JavascriptInterface public void shareText(String raw) {
      if (raw == null) return;
      final String txt = raw.substring(0, Math.min(raw.length(), 300000));
      runOnUiThread(() -> {
        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("text/plain");
        share.putExtra(Intent.EXTRA_SUBJECT, "WAYPACK AI — мой чемодан");
        share.putExtra(Intent.EXTRA_TEXT, txt);
        try { startActivity(Intent.createChooser(share, "Поделиться списком")); }
        catch (ActivityNotFoundException ignored) {}
      });
    }

    @JavascriptInterface public void saveText(String raw) {
      if (raw == null) return;
      final String txt = raw.substring(0, Math.min(raw.length(), 300000));
      runOnUiThread(() -> {
        textToSave = txt;
        Intent save = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        save.addCategory(Intent.CATEGORY_OPENABLE);
        save.setType("text/plain");
        save.putExtra(Intent.EXTRA_TITLE, "waypack-list.txt");
        try { startActivityForResult(save, SAVE_TEXT); }
        catch (ActivityNotFoundException ignored) {}
      });
    }
  }

  @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    super.onActivityResult(requestCode, resultCode, data);
    if (requestCode != SAVE_TEXT || resultCode != RESULT_OK || data == null || data.getData() == null) return;
    try (OutputStream out = getContentResolver().openOutputStream(data.getData())) {
      if (out != null) out.write(("\uFEFF" + textToSave).getBytes(StandardCharsets.UTF_8));
    } catch (Exception e) {
      android.widget.Toast.makeText(this, "Не удалось сохранить файл", android.widget.Toast.LENGTH_LONG).show();
    } finally { textToSave = ""; }
  }

  @Override public void onBackPressed() {
    view.evaluateJavascript("Boolean(window.waypackGoBack && window.waypackGoBack())", value -> {
      if (!"true".equals(value)) MainActivity.super.onBackPressed();
    });
  }

  @Override protected void onDestroy() {
    if (view != null) {
      view.removeJavascriptInterface("WaypackNative");
      view.destroy();
      view = null;
    }
    super.onDestroy();
  }
}
