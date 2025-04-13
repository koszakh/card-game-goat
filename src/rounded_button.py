import tkinter as tk

class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command=None, radius=10, bg="SystemButtonFace", fg="black", font=("Arial", 12)):
        super().__init__(master, width=100, height=30, highlightthickness=0, bd=0)
        self.radius = radius
        self.text = text
        self.command = command
        self.bg_color = bg
        self.fg_color = fg
        self.font = font
        self.is_pressed = False

        self._draw()

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        r = min(self.radius, width // 2, height // 2)

        # Закругленный прямоугольник
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90, fill=self.bg_color, outline=self.bg_color)
        self.create_arc(width - 2 * r, 0, width, 2 * r, start=0, extent=90, fill=self.bg_color, outline=self.bg_color)
        self.create_arc(0, height - 2 * r, 2 * r, height, start=180, extent=90, fill=self.bg_color, outline=self.bg_color)
        self.create_arc(width - 2 * r, height - 2 * r, width, height, start=270, extent=90, fill=self.bg_color, outline=self.bg_color)
        self.create_rectangle(r, 0, width - r, height, fill=self.bg_color, outline=self.bg_color)
        self.create_rectangle(0, r, width, height - r, fill=self.bg_color, outline=self.bg_color)

        # Текст - центрируем по ширине и высоте
        self.create_text(width // 2, height // 2, text=self.text, font=self.font, fill=self.fg_color, anchor=tk.CENTER)

    def configure(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "command" in kwargs:
            self.command = kwargs["command"]
        if "bg" in kwargs:
            self.bg_color = kwargs["bg"]
        if "fg" in kwargs:
            self.fg_color = kwargs["fg"]
        if "font" in kwargs:
            self.font = kwargs["font"]
        self._draw()

    def _on_press(self, event):
        self.is_pressed = True
        self.config(relief=tk.SUNKEN) # Визуальный эффект нажатия

    def _on_release(self, event):
        if self.is_pressed and self.command:
            self.command()
        self.is_pressed = False
        self.config(relief=tk.RAISED) # Возвращаем к обычному виду