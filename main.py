import tkinter as tk
import numpy as np
import cv2 as cv
from skimage import io
from tkinter import filedialog
from PIL import ImageTk, Image
from enum import Enum

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

class Modes(Enum):
    NONE = 0
    ADD_SRC = 1
    ADD_DEST = 2
    READY = 3

class AffineTransformController:

    def __init__(self):
        self.clear_points()

    def change_mode(self, mode):
        if type(mode) != Modes:
            raise TypeError("Expected object Modes, but received "  + str(type(mode)))
        self.mode = mode

    def set_src_points(self):
        self.change_mode(Modes.ADD_SRC)

    def set_dest_points(self):
        self.change_mode(Modes.ADD_DEST)

    def add_point(self, event):
        point = self.event_to_point(event)

        if self.mode == Modes.ADD_SRC:
            self.src_points.append(point)
            if len(self.src_points) > 3:
                self.src_points.pop(0)
            print(self.src_points)

        if self.mode == Modes.ADD_DEST:
            self.dest_points.append(point)
            if len(self.dest_points) > 3:
                self.dest_points.pop(0)
            print(self.dest_points)

        if len(self.src_points) == 3 and len(self.dest_points) == 3:
            self.change_mode(Modes.READY)

        return self.mode

    def clear_points(self):
        self.src_points = []
        self.dest_points = []
        self.matrix = 0
        self.mode = Modes.NONE

    def event_to_point(self, event):
        point = [event.x, event.y]
        return point

    def get_matrix(self):
        src_arr = np.array(self.src_points).astype(np.float32)
        dest_arr = np.array(self.dest_points).astype(np.float32)
        print(src_arr, dest_arr)
        matrix = cv.getAffineTransform(src_arr, dest_arr)
        matrix = np.append(matrix, [[0,0,1]], axis=0)
        print(matrix)
        matrix = np.linalg.inv(matrix)
        print(matrix)
        if matrix[0][0] + matrix[1][1] < 2:
            print("уменьшение!")
        else:
            print("увеличение!")
        self.matrix = matrix

    def get_point(self, point):
        if type(self.matrix) == int:
            self.get_matrix()
        point = np.array(point + [1]).astype(np.float32)
        return self.matrix.dot(point)


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.affine_controller = AffineTransformController()

        self.frame_left = tk.Frame(self)
        self.frame_left.pack(side="left")

        self.button1 = tk.Button(self.frame_left, text="Открыть картинку", command=self.open_image)
        self.button1.pack()

        self.gridbox = convolution_grid(self.frame_left)
        self.gridbox.pack()

        self.convolute_button = tk.Button(self.frame_left, text="Провести операцию свёртки", command=self.convolute_command)
        self.convolute_button.pack()

        self.frame_right = tk.Frame(self)
        self.frame_right.pack(side="right")

        self.button_src = tk.Button(self.frame_right, text="Выбор точек источника", command=self.affine_controller.set_src_points)
        self.button_src.pack()

        self.button_dest = tk.Button(self.frame_right, text="Выбор точек приёмника", command=self.affine_controller.set_dest_points)
        self.button_dest.pack()

        self.button_clr = tk.Button(self.frame_right, text="Удалить точки", command=self.affine_controller.clear_points)
        self.button_clr.pack()

        self.button_transform = tk.Button(self.frame_right, text="Провести аффинную трансформацию", state="disabled", command=self.affine_command)
        self.button_transform.pack()

        self.canva = tk.Canvas(self, width=400, height=400, bg='white')
        self.canva.bind('<Button-1>', self.add_point)
        self.canva.pack(side="bottom")



    def open_image(self):
        path = filedialog.askopenfilename(title='open')
        pil_img = Image.open(path)
        self.image_array = np.array(pil_img)
        self.img = ImageTk.PhotoImage(pil_img)

        w = self.img.width()
        h = self.img.height()
        self.canva.config(width = w, height = h)
        self.image_cont = self.canva.create_image((w/2,h/2), image=self.img)

    def convolute_command(self):
        start_array = self.image_array.copy().astype("int")
        shape = self.image_array.shape
        kernel = self.gridbox.get_values()
        sum = np.array(kernel).sum()
        sum = sum if sum != 0 else 1

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

    def affine_command(self):
        start_array = self.image_array.copy()
        start_array = start_array
        shape = self.image_array.shape
        print(shape)

        for i in range(shape[0]):
            for j in range(shape[1]):
                point = self.affine_controller.get_point([i, j])
                point = np.rint(point).astype("int")

                #print(point)
                if point[0] < 0 or point[1] < 0 or point[0] >= shape[0] or point[1] >= shape[1]:
                    self.image_array[j][i] = [255,255,255]
                else:
                    self.image_array[j][i] = start_array[point[1]][point[0]]
        #self.affine_controller.get_point([0,0])
        #self.image_array = cv.warpAffine(start_array, self.affine_controller.matrix[:2], (shape[1], shape[0]), cv.WARP_INVERSE_MAP)
        self.update_image()

    def bilinear_interpolation(self, point_float):
        x,y = point_float[0], point_float[1]
        fx, fy = np.floor(x), np.floor(y)
        cx, cy = np.ceil(x), np.ceil(y)

        return (self.image_array[fx, fy] * (cx - x) +
               self.image_array[cx, fy] * (x - fx)) * (cy - y) + \
               (self.image_array[fx, cy] * (cx - x) +
                self.image_array[cx, cy] * (x - fx)) * (y - fy)

    def add_point(self, event):
        if self.affine_controller.mode == Modes.READY:
            return

        ret = self.affine_controller.add_point(event)
        if ret != Modes.NONE:
            self.canva.create_oval(event.x - 5, event.y - 5, event.x + 5, event.y + 5, fill=('green','blue')[ret == Modes.ADD_SRC], tags=["base_point"])
        if ret == Modes.READY:
            self.button_transform['state'] = 'normal'





def main():
    root = App()

    root.mainloop()

if __name__ == '__main__':
    main()