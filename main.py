import os
import tkinter as tk
import subprocess
import json
from PIL import Image, ImageTk
from natsort import natsorted
from deserialize import extract_json_files

DIFF = 150

class ImageViewer(tk.Frame):
    def __init__(self, master, image_list, images_path, folders_with_annotations, saved_data_path, final_output_path):
        tk.Frame.__init__(self, master)
        self.master = master
        self.image_list = image_list
        self.images_path = images_path
        self.folders_with_annotations = folders_with_annotations
        self.saved_data_path = saved_data_path
        self.final_output_path = final_output_path
        self.image_count = len(image_list)
        self.active_point = -1
        self.selected_annotation = -1
        self.last_selected_annotation = -1
        self.current_image_index = 0
        self.current_image_name = None
        self.new_annotation_id = 1000000
        self.scale_factor = 1
        self.current_folder = None

        self.canvas = tk.Canvas(self.master, width=1068, height=1068)
        self.canvas.pack(side='left')

        self.label = tk.Label(self.master, text="", font=("Arial", 18))
        self.label.pack(side='top')

        self.create_button = tk.Button(self.master, text="Create Annotation", command=self.create_annotation)
        self.create_button.pack()

        self.open_button = tk.Button(self.master, text="Open Original File", command=self.open_original_file)
        self.open_button.pack()

        self.use_saved_data()
        self.load_image()
        self.draw_annotations()

        self.canvas.bind("<Double-Button-1>", self.on_double_click)
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
        self.folders_with_annotations[self.current_folder][self.current_image_name].append(
            {'id':annotation_id,
             'category': 'parking_space',
             'corner_property': ['visible', 'visible', 'covered', 'covered'],
             'T_or_L': ['L', 'L'],
             'keypoints': points,
             'parking_slot_property_1': ['idle']})
        self.canvas.delete("annotation")
        self.draw_annotations()
        self.save_annotations()

    def load_image(self):
        self.label.config(text=f"{self.current_image_index + 1} / {self.image_count}")

        # get image from file
        image_name = self.image_list[self.current_image_index]
        self.current_image_name = image_name.split('#')[-1]
        self.current_folder = image_name.split('#')[-3]
        image_path = os.path.join(self.images_path, image_name)
        image = Image.open(image_path)
        
        self.canvas.config(width=int(self.scale_factor*image.width), height=int(self.scale_factor*image.height))
        self.photo = ImageTk.PhotoImage(image)

        self.image_object = self.canvas.create_image(int(self.scale_factor*image.width)/2,
                                                     int(self.scale_factor*image.height)/2,
                                                     anchor="center", image=self.photo)
        
        self.master.title(self.current_image_name)

    def draw_annotations(self):
        for annotation in self.folders_with_annotations[self.current_folder][self.current_image_name]:
            points = [self.scale_factor * i for i in annotation['keypoints']]
            self.canvas.create_polygon(points, fill='', outline='red', width=2, tags="annotation")
            for x, y in zip(points[::2], points[1::2]):
                self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="green", tags="annotation")
            for i in range(0, len(points), 2):
                self.canvas.create_text(points[i], points[i+1], text=str(i//2 + 1), tags="annotation")
    
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

    def on_double_click(self, event):
        for i, annotation in enumerate(self.folders_with_annotations[self.current_folder][self.current_image_name]):
            for j in range(0, len(annotation['keypoints']), 2):
                x, y = self.scale_factor * annotation['keypoints'][j], self.scale_factor * annotation['keypoints'][j+1]
                if abs(x - event.x) <= 5 and abs(y - event.y) <= 5:
                    self.select_corner_property(event)
                    return

    def select_corner_property(self, event):
        def close_window():
            print("annotation:", self.folders_with_annotations[self.current_folder][self.current_image_name][self.last_selected_annotation])
            print("Selected property:", selected_property.get())
            self.folders_with_annotations[self.current_folder][self.current_image_name][self.last_selected_annotation]['corner_property'][self.active_point // 2] = selected_property.get()
            if corner_num in [1, 2]:
                print("Selected T_or_L:", selected_T_or_L.get())
                self.folders_with_annotations[self.current_folder][self.current_image_name][self.last_selected_annotation]['T_or_L'][corner_num - 1] = selected_T_or_L.get()
            selection_window.destroy()
        def close_window_without_saving(event):
            selection_window.destroy()
        
        selection_window = tk.Toplevel(self.master)
        corner_num = self.active_point // 2 + 1
        selection_window.title(corner_num)
        selection_window.geometry(f"+{event.x_root}+{event.y_root}")
        selection_window.bind("<FocusOut>", close_window_without_saving)
        
        curAnnotation = self.folders_with_annotations[self.current_folder][self.current_image_name][self.last_selected_annotation]

        # coner property
        initial_property = curAnnotation['corner_property'][self.active_point // 2]
        selected_property = tk.StringVar(value=initial_property)

        option_v = tk.Radiobutton(selection_window, text="visible", variable=selected_property, value="visible")
        option_c = tk.Radiobutton(selection_window, text="covered", variable=selected_property, value="covered")
        option_t = tk.Radiobutton(selection_window, text="truncated", variable=selected_property, value="truncated")
        option_v.pack()
        option_c.pack()
        option_t.pack()

        if curAnnotation['category'] == 'parking_space' and corner_num in [1, 2]:
            # separator
            separator = tk.Frame(selection_window, height=2, bd=1, relief=tk.SUNKEN)
            separator.pack(fill=tk.X, padx=5, pady=5)

            # T or L
            initial_T_or_L = curAnnotation['T_or_L'][corner_num - 1]
            selected_T_or_L = tk.StringVar(value=initial_T_or_L)
            option_T = tk.Radiobutton(selection_window, text="T", variable=selected_T_or_L, value="T")
            option_L = tk.Radiobutton(selection_window, text="L", variable=selected_T_or_L, value="L")
            option_T.pack()
            option_L.pack()

        # confirm button
        confirm_button = tk.Button(selection_window, text="Confirm", command=close_window)
        confirm_button.pack()

    def on_click(self, event):
        self.active_point = -1
        self.selected_annotation = -1
        self.last_selected_annotation = -1
        self.canvas.delete("highlight")
        for i, annotation in enumerate(self.folders_with_annotations[self.current_folder][self.current_image_name]):
            for j in range(0, len(annotation['keypoints']), 2):
                x, y = self.scale_factor * annotation['keypoints'][j], self.scale_factor * annotation['keypoints'][j+1]
                if abs(x - event.x) <= 5 and abs(y - event.y) <= 5:
                    self.selected_annotation = i
                    self.last_selected_annotation = i
                    self.active_point = j
                    self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, outline="yellow", tags="highlight")
                    return

    def on_drag(self, event):
        if self.active_point != -1:
            self.folders_with_annotations[self.current_folder][self.current_image_name][self.selected_annotation]['keypoints'][self.active_point] = event.x / self.scale_factor
            self.folders_with_annotations[self.current_folder][self.current_image_name][self.selected_annotation]['keypoints'][self.active_point + 1] = event.y / self.scale_factor
            self.canvas.delete("annotation")
            self.draw_annotations()

            self.canvas.delete("highlight")
            self.canvas.create_oval(event.x - 5, event.y - 5, event.x + 5, event.y + 5, outline="yellow", tags="highlight")
        # else:
        #     self.canvas.move(self.image_object, event.x, event.y)

    def on_release(self, event):
        self.selected_annotation = -1
        self.save_annotations()

    def delete_annotation(self, event):
        if self.last_selected_annotation != -1:
            self.folders_with_annotations[self.current_folder][self.current_image_name].pop(self.last_selected_annotation)
            self.active_point = -1
            self.last_selected_annotation = -1
            self.canvas.delete("annotation")
            self.canvas.delete("highlight")
            self.draw_annotations()
            self.save_annotations()

    def save_annotations(self):
        with open("annotations.txt", 'w+') as file:
            for annotation in self.folders_with_annotations[self.current_folder][self.current_image_name]:
                corners_str = ' '.join(f"{annotation['corner_property'][i // 2]} {annotation['keypoints'][i] - DIFF} {annotation['keypoints'][i+1] - DIFF}" for i in range(0, len(annotation['keypoints']), 2))
                line = f"{annotation['id']} " + corners_str + "\n"
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

    def save_json(self):
        if not os.path.exists('results'):
            os.makedirs('results')
        for folder_name, annotations in self.folders_with_annotations.items():
            # craete sub folder
            folder_path = os.path.join('results', folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            # minus DIFF from all keypoints
            for img_name in annotations:
                for i in range(len(annotations[img_name])):
                    annotations[img_name][i]['keypoints'] = [i - DIFF for i in annotations[img_name][i]['keypoints']]
            # export as json
            json_file_path = os.path.join(folder_path, 'corrected_result.json')
            with open(json_file_path, 'w') as json_file:
                json.dump(annotations, json_file, indent=4)

    def save_data(self):
        with open(self.saved_data_path, "w") as file:
            file.write(str(self.current_image_index))
            file.write('\n')
            file.write(str(self.new_annotation_id))
        self.save_json()


    def open_original_file(self):
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

def read_images(images_path, folders_with_annotations, saved_data_path, final_output_path):
    file_list = os.listdir(images_path)
    image_files = [file for file in file_list if file.endswith(".jpg") or file.endswith(".bmp")]
    image_files = natsorted(image_files)
    
    root = tk.Tk()
    viewer = ImageViewer(root, image_files, images_path, folders_with_annotations, saved_data_path, final_output_path)
    root.protocol("WM_DELETE_WINDOW", viewer.quit)
    root.mainloop()
    
# image folder
images_path = "JSON/haitian_12800/line_error_found"
# file displaying current image annotations
annotations_path = "annotations.txt"
# file recording 
# (1) the index of the last accessed image and 
# (2) the next available annotation index
saved_data_path = "saved_data.txt"
# folder recording output json
final_output_path = "final_output.json"
# folder containing original JSON
json_folder = 'JSON/haitian_12800'

# dict(parent_folder_name -> dict(file_name -> list of annotation dicts))
folders_with_annotations = extract_json_files(json_folder)

read_images(images_path, folders_with_annotations, saved_data_path, final_output_path)
