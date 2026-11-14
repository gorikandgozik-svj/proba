"""Windows desktop front end for CINEMA FORGE. Tk stays on the main thread."""
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from .pipeline import Job, execute
from .media import PROFILES
from .cloud import MODEL
from .voices import get_voices, sync

BG = '#0b101a'
PANEL = '#141d2b'
INK = '#e8f0fc'
MUTED = '#9caec2'
CYAN = '#58dfcb'

class Studio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CINEMA FORGE  •  AI Video Studio 0.1')
        self.geometry('1030x770')
        self.minsize(840, 660)
        self.configure(bg=BG)
        self.pipe = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.mode = tk.StringVar(value='Preview (motion graphics)')
        self.model = tk.StringVar(value='Kling 3.0 4K')
        self.profile = tk.StringVar(value='4K UHD / 60 FPS')
        self.language = tk.StringVar(value='auto')
        self.narration = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Готов к работе')
        self.dst = tk.StringVar(value=str(Path.home() / 'Videos' /
                 f'CINEMA_FORGE_{datetime.now():%Y%m%d_%H%M}.mp4'))
        self._build()
        self.after(100, self._poll)
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _label(self, parent, text, size=11, color=INK, bold=False, **kw):
        return tk.Label(parent, text=text, fg=color, bg=parent.cget('bg'),
                        font=('Segoe UI', size, 'bold' if bold else 'normal'), **kw)

    def _field(self, parent, variable, show=None, width=30):
        return tk.Entry(parent, textvariable=variable, bg='#1a2636', fg=INK,
                        insertbackground=INK, selectbackground='#1c6b74', relief='flat',
                        font=('Segoe UI', 11), width=width, show=show)

    def _select(self, parent, var, options, width=24):
        s = ttk.Combobox(parent, values=options, state='readonly', textvariable=var, width=width)
        return s

    def _build(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', foreground=INK, fieldbackground='#1a2636',
                        background='#1a2636', bordercolor='#25384c', arrowcolor=CYAN,
                        font=('Segoe UI', 10))
        style.map('TCombobox', fieldbackground=[('readonly', '#1a2636')],
                  foreground=[('readonly', INK)])
        style.configure('F.Horizontal.TProgressbar', background=CYAN,
                        troughcolor='#26354b', borderwidth=0)
        root = tk.Frame(self, bg=BG, padx=28, pady=20)
        root.pack(fill='both', expand=True)
        self._label(root, 'CINEMA  FORGE', size=28, color=CYAN, bold=True).pack(anchor='w')
        self._label(root, 'AI CLIP PIPELINE   /   STORYBOARD  ·  VOICES  ·  RENDER',
                    size=10, color=MUTED).pack(anchor='w', pady=(0, 18))

        card = tk.Frame(root, bg=PANEL, padx=18, pady=14)
        card.pack(fill='x', pady=(0, 12))
        self._label(card, '01  ПРОМПТ ДЛЯ ФИЛЬМА', 11, CYAN, True).pack(anchor='w')
        self.prompt = tk.Text(card, height=6, bg='#101824', fg=INK,
                              insertbackground=INK, relief='flat', wrap='word',
                              font=('Segoe UI', 12), padx=12, pady=9)
        self.prompt.pack(fill='x', pady=(9, 0))
        self.prompt.insert('1.0', 'Кинематографичная реклама суперкара: дождливый мегаполис ночью, '
                                  'мокрый асфальт, реалистичные отражения, динамичные пролёты камеры.')

        options = tk.Frame(root, bg=PANEL, padx=18, pady=13)
        options.pack(fill='x', pady=(0, 12))
        self._label(options, '02  ДВИЖОК И ЭКСПОРТ', 11, CYAN, True).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 9))
        fields = [
            ('Режим', self.mode, ['Preview (motion graphics)', 'Cloud AI video']),
            ('Облачная модель', self.model, list(MODEL)),
            ('Экспорт', self.profile, list(PROFILES)),
            ('Язык озвучки', self.language, ['auto', 'ru', 'en', 'es', 'it', 'de']),
        ]
        for i, (title, variable, vals) in enumerate(fields):
            self._label(options, title, 10, MUTED).grid(row=1, column=i, sticky='w', padx=(0, 12))
            self._select(options, variable, vals, 24 if i < 3 else 13).grid(row=2, column=i, sticky='ew', padx=(0, 13), pady=(4, 11))
        options.grid_columnconfigure(0, weight=2)
        options.grid_columnconfigure(1, weight=2)
        options.grid_columnconfigure(2, weight=2)
        options.grid_columnconfigure(3, weight=1)
        self._label(options, 'Runway API key (только облачный режим)', 10, MUTED).grid(
            row=3, column=0, columnspan=2, sticky='w')
        self.key = tk.StringVar(value=os.environ.get('RUNWAYML_API_SECRET', ''))
        self._field(options, self.key, show='•', width=37).grid(
            row=4, column=0, columnspan=2, sticky='ew', padx=(0, 14), pady=(4, 0))
        tk.Checkbutton(options, text='Создать нейроозвучку (интернет)', variable=self.narration,
                       bg=PANEL, fg=INK, activebackground=PANEL, activeforeground=INK,
                       selectcolor=BG, font=('Segoe UI', 10)).grid(row=4, column=2, columnspan=2, sticky='w')

        dest = tk.Frame(root, bg=PANEL, padx=18, pady=12)
        dest.pack(fill='x', pady=(0, 12))
        self._label(dest, '03  СОХРАНИТЬ ВИДЕО В', 11, CYAN, True).pack(anchor='w')
        row = tk.Frame(dest, bg=PANEL)
        row.pack(fill='x', pady=(8, 0))
        self._field(row, self.dst, width=75).pack(side='left', expand=True, fill='x', padx=(0, 9))
        tk.Button(row, text='Выбрать…', command=self._browse, bg='#2a3c50', fg=INK,
                  relief='flat', padx=12, pady=5).pack(side='right')

        actions = tk.Frame(root, bg=BG)
        actions.pack(fill='x', pady=(2, 11))
        self.start_btn = tk.Button(actions, text='▶  СОЗДАТЬ ФИЛЬМ', command=self._start,
                                   bg=CYAN, fg='#0b1822', relief='flat',
                                   font=('Segoe UI', 13, 'bold'), padx=30, pady=11)
        self.start_btn.pack(side='left')
        self.stop_btn = tk.Button(actions, text='■  ОТМЕНА', command=self._stop,
                                  bg='#49303c', fg='#ffd4dd', relief='flat',
                                  font=('Segoe UI', 11, 'bold'), padx=18, pady=13,
                                  state='disabled')
        self.stop_btn.pack(side='left', padx=10)
        tk.Button(actions, text='Проверить голоса', command=self._check_voices,
                  bg='#20324a', fg=INK, relief='flat', padx=15, pady=14).pack(side='right')

        status_row = tk.Frame(root, bg=BG)
        status_row.pack(fill='x')
        self._label(status_row, '04  ЛОГ СБОРКИ', 10, CYAN, True).pack(side='left')
        tk.Label(status_row, textvariable=self.status, bg=BG, fg=MUTED,
                 font=('Segoe UI', 10)).pack(side='right')
        self.bar = ttk.Progressbar(root, mode='determinate', style='F.Horizontal.TProgressbar')
        self.bar.pack(fill='x', pady=(9, 9))
        self.log = tk.Text(root, bg='#0e1724', fg='#cad9e7', relief='flat',
                           font=('Consolas', 10), height=10, state='disabled', padx=11, pady=9)
        self.log.pack(fill='both', expand=True)
        self._write('Качество исходника зависит от AI-модели. 4K/60 при экспорте не означает 4K/60 исходных AI-кадров.')
        self._write('Preview создаёт анимированную графику; Cloud AI video требует оплачиваемый API.')

    def _browse(self):
        path = filedialog.asksaveasfilename(title='Сохранить MP4', defaultextension='.mp4',
                                          filetypes=[('Видео MPEG-4', '*.mp4')], initialfile=Path(self.dst.get()).name)
        if path:
            self.dst.set(path)

    def _write(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', f'• {text}\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        prompt = self.prompt.get('1.0', 'end').strip()
        if not prompt:
            messagebox.showerror('Промпт', 'Напиши, что нужно показать в фильме.')
            return
        output = Path(self.dst.get()).expanduser()
        if output.suffix.lower() != '.mp4':
            messagebox.showerror('Сохранение', 'Укажи путь к MP4-файлу.')
            return
        if self.mode.get() == 'Cloud AI video':
            if not self.key.get().strip():
                messagebox.showerror('Облачный режим', 'Для AI-видео нужен действующий Runway API key. '
                                     'Без ключа доступен Preview — не AI-видео.')
                return
            if not messagebox.askyesno('Платная AI-генерация',
                'Будут отправлены 12 отдельных запросов по 10 секунд к платному API.\n'
                'Расходы могут быть существенными. Продолжить?'):
                return
        elif self.profile.get() == '4K UHD / 60 FPS':
            if not messagebox.askyesno('Тяжёлый экспорт',
                'Превью в 4K/60 рендерится процессором и на старом ПК может работать очень долго.\n'
                'Для проверки лучше выбрать 720p/24. Продолжить?'):
                return
        self.cancel = threading.Event()
        job = Job(prompt=prompt, destination=output, mode=self.mode.get(), model=self.model.get(),
                  profile=self.profile.get(), language=self.language.get(),
                  narration=self.narration.get(), api_key=self.key.get())
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.bar['value'] = 0
        self.status.set('Обработка...')
        def task():
            try:
                result = execute(job, log=lambda x: self.pipe.put(('log', x)),
                                 progress=lambda p: self.pipe.put(('progress', p)), cancel=self.cancel)
                self.pipe.put(('done', str(result)))
            except Exception as exc:
                self.pipe.put(('fail', str(exc)))
        self.worker = threading.Thread(target=task, daemon=True)
        self.worker.start()

    def _check_voices(self):
        def task():
            try:
                voices = sync(get_voices('all'))
                count = {k: sum(any(v.locale.startswith(prefix) for prefix in prefixes)
                                 for v in voices) for k, prefixes in {
                    'RU': ('ru-RU',), 'EN': ('en-US','en-GB','en-AU'),
                    'ES': ('es-ES','es-MX'), 'IT': ('it-IT',), 'DE': ('de-DE',)
                }.items()}
                self.pipe.put(('log', 'Реальные нейроголоса онлайн: ' + ', '.join(f'{k}={v}' for k,v in count.items())))
            except Exception as exc:
                self.pipe.put(('log', f'Список голосов сейчас недоступен: {exc}'))
        threading.Thread(target=task, daemon=True).start()

    def _stop(self):
        self.cancel.set()
        self.status.set('Отмена...')

    def _poll(self):
        try:
            for _ in range(80):
                kind, payload = self.pipe.get_nowait()
                if kind == 'log':
                    self._write(payload)
                elif kind == 'progress':
                    self.bar['value'] = int(float(payload) * 100)
                elif kind in ('done', 'fail'):
                    self.start_btn.configure(state='normal')
                    self.stop_btn.configure(state='disabled')
                    if kind == 'done':
                        self.status.set('Экспорт завершён')
                        self._write(f'Результат сохранён: {payload}')
                        messagebox.showinfo('Экспорт готов', f'Видео сохранено:\n{payload}')
                    else:
                        self.status.set('Ошибка')
                        self._write('ОШИБКА: ' + payload)
                        messagebox.showerror('Экспорт не завершён', payload)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno('Отмена рендера', 'Остановить текущий рендер и закрыть программу?'):
                return
            self.cancel.set()
        self.destroy()


def main():
    Studio().mainloop()

if __name__ == '__main__':
    main()
