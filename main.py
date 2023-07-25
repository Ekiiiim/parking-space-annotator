import os
import tkinter as tk
import subprocess
import json
from PIL import Image, ImageTk
from natsort import natsorted

DIFF = 98

class ImageViewer(tk.Frame):
    def __init__(self, master, image_list, images_path, annotations, saved_data_path):
        tk.Frame.__init__(self, master)
        self.master = master
        self.image_list = image_list
        self.images_path = images_path
        self.annotations = annotations
        self.saved_data_path = saved_data_path
        self.image_count = len(image_list)
        self.active_point = -1
        self.selected_annotation = -1
        self.last_selected_annotation = -1
        self.current_image_index = 0
        self.current_image_name = None
        self.new_annotation_id = 1000000

        self.canvas = tk.Canvas(self.master, width=1062, height=1062)
        self.canvas.pack()

        self.label = tk.Label(self.master, text="", font=("Arial", 18))
        self.label.pack()

        self.create_button = tk.Button(self.master, text="Create Annotation", command=self.create_annotation)
        self.create_button.pack()

        self.use_saved_data()
        self.load_image()
        self.draw_annotations()

        self.canvas.bind("<Double-Button-1>", self.open_original_file)
        self.master.bind("<Left>", self.previous_image)
        self.master.bind("<Right>", self.next_image)
        self.master.bind("<Button-1>", self.on_click)
        self.master.bind("<B1-Motion>", self.on_drag)
        self.master.bind("<ButtonRelease-1>", self.on_release)
        self.master.bind('<BackSpace>', self.delete_annotation)

    def create_annotation(self):
        annotation_id = self.new_annotation_id
        self.new_annotation_id += 1
        points = [400, 400, 600, 400, 600, 500, 400, 500]
        self.annotations[self.current_image_name].append(
            {'id':annotation_id,
             'category': 'parking_space',
             'corner_property': ['visible', 'visible', 'covered', 'covered'],
             'keypoints': points,
             'parking_slot_property_1': ['idle']})
        self.canvas.delete("annotation")
        self.draw_annotations()
        self.save_annotations()

    def load_image(self):
        self.label.config(text=f"{self.current_image_index + 1} / {self.image_count}")
        image_name = self.image_list[self.current_image_index]
        self.current_image_name = image_name.split('#')[-1]
        image_path = os.path.join(self.images_path, image_name)
        image = Image.open(image_path)
        self.canvas.config(width=int(0.9*image.width), height=int(0.9*image.height))
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(int(0.9*image.width)/2, 
                                 int(0.9*image.height)/2, 
                                 anchor="center", image=self.photo)
        
        self.master.title(self.current_image_name)

    def draw_annotations(self):
        for annotation in self.annotations[self.current_image_name]:
            points = [i + DIFF for i in annotation['keypoints']]
            self.canvas.create_polygon(points, fill='', outline='red', width=2, tags="annotation")
            for x, y in zip(points[::2], points[1::2]):
                self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="green", tags="annotation")
            for i in range(0, len(points), 2):
                self.canvas.create_text(points[i], points[i+1], text=str(i//2 + 1), tags="annotation")
    

    # def load_annotations(self):
    #     with open(self.annotate_path, 'r') as f:
    #         lines = f.readlines()
    #         for line in lines:
    #             id_and_points = line.split()
    #             annotation_id = id_and_points[0]
    #             points = [float(x) for x in id_and_points[1:]]
    #             self.annotations.append((annotation_id, points))

    # def draw_annotations(self):
    #     for annotation in self.annotations:
    #         points = annotation[1]
    #         self.canvas.create_polygon(points, fill='', outline='red', width=2, tags="annotation")
    #         for x, y in zip(points[::2], points[1::2]):
    #             self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="green", tags="annotation")
    #         for i in range(0, len(points), 2):
    #             self.canvas.create_text(points[i], points[i+1], text=str(i//2 + 1), tags="annotation")
    
    def previous_image(self, event):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_image()
            self.draw_annotations()

    def next_image(self, event):
        if self.current_image_index < len(self.image_list) - 1:
            self.current_image_index += 1
            self.load_image()
            self.draw_annotations()

    def on_click(self, event):
        self.active_point = -1
        self.selected_annotation = -1
        self.last_selected_annotation = -1
        self.canvas.delete("highlight")
        for i, annotation in enumerate(self.annotations[self.current_image_name]):
            for j in range(0, len(annotation['keypoints']), 2):
                x, y = annotation['keypoints'][j] + DIFF, annotation['keypoints'][j+1] + DIFF
                if abs(x - event.x) <= 5 and abs(y - event.y) <= 5:
                    self.selected_annotation = i
                    self.last_selected_annotation = i
                    self.active_point = j
                    self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, outline="yellow", tags="highlight")
                    break

    def on_drag(self, event):
        if self.active_point != -1:
            self.annotations[self.current_image_name][self.selected_annotation]['keypoints'][self.active_point] = event.x - DIFF
            self.annotations[self.current_image_name][self.selected_annotation]['keypoints'][self.active_point + 1] = event.y - DIFF
            self.canvas.delete("annotation")
            self.draw_annotations()

            self.canvas.delete("highlight")
            self.canvas.create_oval(event.x - 5, event.y - 5, event.x + 5, event.y + 5, outline="yellow", tags="highlight")

    def on_release(self, event):
        self.active_point = -1
        self.selected_annotation = -1
        self.save_annotations()

    def delete_annotation(self, event):
        if self.last_selected_annotation != -1:
            self.annotations[self.current_image_name].pop(self.last_selected_annotation)
            self.canvas.delete("annotation")
            self.draw_annotations()
            self.save_annotations()

    def save_annotations(self):
        with open("annotations.txt", 'w+') as file:
            for annotation in self.annotations[self.current_image_name]:
                line = f"{annotation['id']} {' '.join(str(i - DIFF) for i in annotation['keypoints'])}\n"
                file.write(line)

    def use_saved_data(self):
        if os.path.exists(self.saved_data_path):
            with open(self.saved_data_path, "r") as file:
                last_image_index = int(file.readline())
                if last_image_index < len(self.image_list):
                    self.current_image_index = last_image_index
                next_line = file.readline()
                if next_line:
                    self.new_annotation_id = int(next_line)
                print(f"current index: {self.current_image_index}  new annotation: {self.new_annotation_id}")

    def save_data(self):
        with open(self.saved_data_path, "w") as file:
            file.write(str(self.current_image_index))
            file.write('\n')
            file.write(str(self.new_annotation_id))


    def open_original_file(self, event):
        image_name = self.image_list[self.current_image_index]
        file_path = os.path.join(self.images_path, image_name)
        # file_path = os.path.abspath(image_path)
        if os.name == 'nt':  # for Windows?
            os.startfile(file_path)
        elif os.name == 'posix':  # for Linux and macOS
            subprocess.Popen(['open', file_path])

    def quit(self):
        self.save_data()
        self.master.destroy()

def initialize():
    with open('result_adjust_order.json', 'r') as file:
        data = json.load(file)
    
    categories = {}
    for d in data['categories']:
        categories[d['id']] = d['name']
    images = {}
    annotations = {}
    for d in data['images']:
        images[d['id']] = d['file_name']
        annotations[d['file_name']] = []

    for d in data['annotations']:
        new_dict = {}
        new_dict['id'] = d['id']
        new_dict['keypoints'] = d['keypoints']
        new_dict['corner_property'] = d['corner_property']
        new_dict['category'] = categories[d['category_id']]
        if new_dict['category'] == "parking_space":
            new_dict['parking_slot_property_1'] = d['parking_slot_property_1']

        image_name = images[d['image_id']]
        annotations[image_name].append(new_dict)
    
    return annotations

def read_images(images_path, annotations_path, saved_data_path):
    file_list = os.listdir(images_path)
    image_files = [file for file in file_list if file.endswith(".jpg") or file.endswith(".bmp")]
    image_files = natsorted(image_files)
    
    root = tk.Tk()
    viewer = ImageViewer(root, image_files, images_path, annotations_path, saved_data_path)
    root.protocol("WM_DELETE_WINDOW", viewer.quit)
    root.mainloop()
    
# image folder
images_path = "/Users/chengminyu/Downloads/line_error_found"
# file recording parking slot annotations
annotations_path = "annotations.txt"
# file recording 
# (1) the index of the last accessed image and 
# (2) the next available annotation index
saved_data_path = "saved_data.txt"

annotations = initialize() # dict(file_name -> list of annotation dicts)

read_images(images_path, annotations, saved_data_path)
