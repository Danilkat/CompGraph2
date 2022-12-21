import tkinter as tk
import numpy as np
from skimage import io
from tkinter import filedialog
from PIL import ImageTk, Image

class convolution_grid(tk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def create_integer_entry(i, j):
            tk.Entry(self, width=2, justify="center", bd=1, textvariable=tk.IntVar()).grid(row=i, column=j)

        for i in range(3):
            for j in range(3):
                create_integer_entry(i, j)

    def get_values(self):
        arr = [[0]*3 for i in range(3)]
        i=0
        for entry in self.winfo_children():
            arr[i//3][i%3] = int(entry.get())
            i+= 1
        return arr

def clamp_to_8bit(value):
    if type(value) != int:
        for i in range(3):
            value[i] = 255 if value[i] > 255 else value[i]
            value[i] = 0 if value[i] < 0 else value[i]
        print(value)
        return value

    value = 255 if value > 255 else value
    value = 0 if value < 0 else value
    return value

def apply_kernel(pixel, kernel):




class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.frame = tk.Frame(self)
        self.frame.pack()

        self.button1 = tk.Button(self.frame, text="Открыть картинку", command=self.open_image)
        self.button1.pack()

        self.gridbox = convolution_grid(self.frame)
        self.gridbox.pack()

        self.convolute_button = tk.Button(self.frame, text="Провести операцию свёртки", command=self.convolute_command)
        self.convolute_button.pack()

        self.canva = tk.Canvas(self.frame, width=400, height=400, bg='white')
        self.canva.pack()

    def open_image(self):
        path = filedialog.askopenfilename(title='open')
        pil_img = Image.open(path)
        self.image_array = np.array(pil_img)
        self.img = ImageTk.PhotoImage(pil_img)

        w = self.img.width() + 50
        h = self.img.height() + 50
        self.canva.config(width = w, height = h)
        self.image_cont = self.canva.create_image((w/2,h/2), image=self.img)

        print(self.image_array[0][0])
        print(self.image_array[0][0] * 2)
        print(type(self.image_array[0][0]))

    def convolute_command(self):
        start_array = self.image_array.copy().astype("int")
        shape = self.image_array.shape
        kernel = self.gridbox.get_values()
        sum = np.array(kernel).sum()
        sum = sum if sum != 0 else 1
        print(sum)

        for i in range(shape[0]):
            for j in range(shape[1]):
                if shape[2]:
                    accumulator = [0,0,0]
                else:
                    accumulator = 0

                for kern_i in range(3):
                    for kern_j in range(3):

                        pix_i = i - 1 + kern_i
                        pix_j = j - 1 + kern_j

                        pix_i = pix_i + 1 if pix_i < 0 else pix_i
                        pix_j = pix_j + 1 if pix_j < 0 else pix_j

                        pix_i = pix_i - 1 if pix_i >= shape[0] else pix_i
                        pix_j = pix_j - 1 if pix_j >= shape[1] else pix_j
                        accumulator += start_array[pix_i][pix_j] * kernel[kern_i][kern_j]
                accumulator = np.round(accumulator / sum).astype("int")
                accumulator = clamp_to_8bit(accumulator)
                self.image_array[i][j] = accumulator
        self.update_image()

    def update_image(self):
        self.img = ImageTk.PhotoImage(Image.fromarray(self.image_array.astype("uint8")))
        self.canva.itemconfig(self.image_cont, image=self.img)




def main():
    root = App()

    root.mainloop()

if __name__ == '__main__':
    main()