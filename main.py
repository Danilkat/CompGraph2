import tkinter as tk

import PIL.Image
import numpy as np
import cv2 as cv
from skimage import io
from tkinter import filedialog
from PIL import ImageTk, Image
from enum import Enum
import warnings
warnings.filterwarnings("error")

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

class Scales(Enum):
    UPSCALE = 0
    DOWNSCALE = 1

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
        if type(event) == tk.Event:
            point = self.event_to_point(event)
        elif type(event) == list:
            point = event

        if self.mode == Modes.ADD_SRC:
            self.src_points.append(point)
            if len(self.src_points) > 3:
                self.src_points.pop(0)

        if self.mode == Modes.ADD_DEST:
            self.dest_points.append(point)
            if len(self.dest_points) > 3:
                self.dest_points.pop(0)

        if len(self.src_points) == 3 and len(self.dest_points) == 3:
            self.get_matrix()
            self.change_mode(Modes.READY)

        return self.mode

    def clear_points(self):
        self.src_points = []
        self.dest_points = []
        self.uninverted_matrix = 0
        self.matrix = 0
        self.mode = Modes.NONE
        self.scale_type = None

    def event_to_point(self, event):
        point = [event.x, event.y]
        return point

    def get_matrix(self):
        src_arr = np.array(self.src_points).astype(np.float32)
        dest_arr = np.array(self.dest_points).astype(np.float32)
        matrix = cv.getAffineTransform(src_arr, dest_arr)
        if matrix[0][0] + matrix[1][1] > 2:
            self.scale_type = Scales.UPSCALE
        else:
            self.scale_type = Scales.DOWNSCALE
        self.uninverted_matrix = matrix
        matrix = np.append(matrix, [[0,0,1]], axis=0)
        matrix = np.linalg.inv(matrix)

        self.matrix = matrix
        return self.matrix

    def get_point(self, point):
        point = np.array(point + [1]).astype(np.float32)
        return (self.matrix.dot(point))[:2]

    def get_reverse_point(self, point):
        point = np.array(point + [1]).astype(np.float32)
        return (self.uninverted_matrix.dot(point))[:2]

    def create_mipmap(self, initial_image_size, mipmap_level):
        self.clear_points()
        w,h = initial_image_size

        self.set_src_points()
        self.add_point([0,h])
        self.add_point([0, 0])
        self.add_point([w, 0])

        self.set_dest_points()
        self.add_point([0,h//mipmap_level])
        self.add_point([0, 0])
        self.add_point([w//mipmap_level, 0])
        self.get_matrix()
        return self



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

        self.is_simpliest = tk.BooleanVar()

        self.check_simpliest = tk.Checkbutton(self.frame_right, text="Использовать простейший алгоритм", variable=self.is_simpliest, onvalue=True, offvalue=False)
        self.check_simpliest.pack()

        self.button_transform = tk.Button(self.frame_right, text="Провести аффинную трансформацию", state="disabled", command=self.affine_command)
        self.button_transform.pack()

        self.canva = tk.Canvas(self, width=400, height=400, bg='white')
        self.canva.bind('<Button-1>', self.add_point)
        self.canva.pack(side="bottom")



    def open_image(self):
        path = filedialog.askopenfilename(title='open')
        pil_img = Image.open(path).convert("RGB")
        self.image_array = np.array(pil_img)
        self.img = ImageTk.PhotoImage(pil_img)

        w = self.img.width()
        h = self.img.height()

        self.image_mipmaps = []
        self.image_mipmaps.append(self.image_array.copy())
        # self.image_mipmaps.append(np.array(pil_img.resize((w//2,h//2))))
        # self.image_mipmaps.append(np.array(pil_img.resize((w//4,h//4))))
        # self.image_mipmaps.append(np.array(pil_img.resize((w//8,h//8))))
        # self.image_mipmaps.append(np.array(pil_img.resize((w//16,h//16))))
        self.image_mipmaps.append(np.array(Image.new("RGB", (w//2, h//2), (255,0,0))))
        self.image_mipmaps.append(np.array(Image.new("RGB", (w//4, h//4), (0,255,0))))
        self.image_mipmaps.append(np.array(Image.new("RGB", (w//8, h//8), (0,0,255))))
        self.image_mipmaps.append(np.array(Image.new("RGB", (w//16, h//16), (255,125,125))))
        self.image_mipmap_controllers = []
        self.image_mipmap_controllers.append(AffineTransformController().create_mipmap((w,h), 1))
        self.image_mipmap_controllers.append(AffineTransformController().create_mipmap((w,h), 2))
        self.image_mipmap_controllers.append(AffineTransformController().create_mipmap((w,h), 4))
        self.image_mipmap_controllers.append(AffineTransformController().create_mipmap((w,h), 8))
        self.image_mipmap_controllers.append(AffineTransformController().create_mipmap((w,h), 16))


        self.canva.config(width = w, height = h)
        self.image_cont = self.canva.create_image((w/2,h/2), image= self.img)

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
        is_downscale = False
        if self.affine_controller.scale_type == Scales.DOWNSCALE:
            is_downscale = True

        for i in range(shape[1]):
            for j in range(shape[0]):
                point = self.affine_controller.get_point([i, j])

                if self.is_simpliest.get():
                    point = np.rint(point).astype("int")
                    self.image_array[j][i] = self.safe_access_image_array(start_array, point[1], point[0])
                else:
                    if is_downscale:
                        self.image_array[j][i] = self.trilinear_interpolation(point)
                    else:
                        self.image_array[j][i] = self.bilinear_interpolation(start_array, point)

        self.update_image()

    def trilinear_interpolation(self, point):
        x, y = point
        fx, fy = np.floor(point)
        cx, cy = np.ceil(point)
        px0 = self.affine_controller.get_reverse_point([fx, y])
        px1 = self.affine_controller.get_reverse_point([cx, y])
        py0 = self.affine_controller.get_reverse_point([x, fy])
        py1 = self.affine_controller.get_reverse_point([x, cy])
        Kx = np.abs(px1[0] - px0[0])
        Ky = np.abs(py1[1] - py0[1])
        try:
            K = 1/(2*Ky) + 1/(2*Kx)
        except RuntimeWarning:
            K = 1.5
        i = 1.0
        m_mipmap_contr = None
        m2_mipmap_contr = None
        m_mipmap_arr = None
        m2_mipmap_arr = None
        for n in range(5):
            if i < K < 2.0 * i:
                m_mipmap_contr = self.image_mipmap_controllers[n]
                m2_mipmap_contr = self.image_mipmap_controllers[n+1]
                m_mipmap_arr = self.image_mipmaps[n]
                m2_mipmap_arr = self.image_mipmaps[n+1]
                break
            i *= 2.0
        print(K)
        m_point = m_mipmap_contr.get_reverse_point(list(point))
        m2_point = m2_mipmap_contr.get_reverse_point(list(point))
        my, mx = np.rint(m_point).astype("int")
        m2y, m2x = np.rint(m2_point).astype("int")
        m_rgb = self.safe_access_image_array(m_mipmap_arr, mx, my)
        m2_rgb = self.safe_access_image_array(m2_mipmap_arr, m2x, m2y)
        return (m_rgb * (i*2 - K) + m2_rgb * (K - i)) / i

    def safe_access_image_array(self, arr, x, y):
        if x < 0 or x >= arr.shape[0]:
            return np.array([0, 0, 0])
        if y < 0 or y >= arr.shape[1]:
            return np.array([0, 0, 0])
        return arr[x, y]

    def bilinear_interpolation(self,arr, point_float):
        y,x = point_float
        fy, fx = np.floor(point_float).astype("int")
        cy, cx = np.ceil(point_float).astype("int")

        return (self.safe_access_image_array(arr, fx, fy) * (cx - x) +
               self.safe_access_image_array(arr, cx, fy) * (x - fx)) * (cy - y) + \
               (self.safe_access_image_array(arr, fx, cy) * (cx - x) +
                self.safe_access_image_array(arr, cx, cy) * (x - fx)) * (y - fy)

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