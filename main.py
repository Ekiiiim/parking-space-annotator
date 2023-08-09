import os
import tkinter as tk
import subprocess
import json
from PIL import Image, ImageTk
from natsort import natsorted
from deserialize import extract_json_files

DIFF = 150

class ImageViewer(tk.Frame):
    def __init__(self, master, image_list, images_path, folders_with_annotations, saved_data_path, final_output_path, json_folder):
        tk.Frame.__init__(self, master)
        self.master = master
        self.image_list = image_list
        self.images_path = images_path
        self.folders_with_annotations = folders_with_annotations
        self.saved_data_path = saved_data_path
        self.final_output_path = final_output_path
        self.json_folder = json_folder
        self.image_count = len(image_list)
        self.active_point = -1
        self.selected_annotation = -1
        self.last_selected_annotation = -1
        self.current_image_index = 0
        self.current_image_name = None
        self.new_annotation_id = 1000000
        self.scale_factor = 0.8
        self.current_folder = None

        self.canvas = tk.Canvas(self.master, width=1068, height=1068)
        self.canvas.pack(side='left')

        self.label = tk.Label(self.master, text="", font=("Arial", 18))
        self.label.pack(side='top')

        self.create_button = tk.Button(self.master, text="Create Annotation", command=self.create_annotation)
        self.create_button.pack()
        self.limiter_button = tk.Button(self.master, text="Create Limiter", width=12, command=self.create_limiter)
        self.limiter_button.pack()

        self.open_button = tk.Button(self.master, text="Open Original File", command=self.open_original_file)
        self.open_button.pack()

        self.slider = tk.Scale(self.master, label='Zoom', resolution=0.1, from_=0.5, to=1.2, orient=tk.VERTICAL, tickinterval=0.1, command=self.reload_image)
        self.slider.set(0.8)
        self.slider.pack()

        self.instructions = tk.Label(self.master, text="\n\n切换图片: 左右键\n\n选中标注: 单击角点\n\n设置角点: 双击\n\n保存设置: Confirm\n\n删除标注: 选中+删除键", font=("Arial", 16))
        self.instructions.pack()

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
            {'keypoints': points,
             'parking_slot_property_1': ['idle'],
             'T_or_L': ['L', 'L'],
             'corner_property': ['visible', 'visible', 'covered', 'covered'],
             'id': annotation_id,
             'image_id': self.folders_with_annotations[self.current_folder][self.current_image_name][0]['image_id'],
             'group_id': 'None',
             'parking_slot_property_2': ['common'],
             'category_id': 2000})
        self.canvas.delete("annotation")
        self.draw_annotations()
        self.save_annotations()

    def create_limiter(self):
        annotation_id = self.new_annotation_id
        self.new_annotation_id += 1
        points = [400, 400, 600, 400]
        self.folders_with_annotations[self.current_folder][self.current_image_name].append(
            {'keypoints': points,
             'corner_property': ['visible', 'visible'],
             'id': annotation_id,
             'image_id': self.folders_with_annotations[self.current_folder][self.current_image_name][0]['image_id'],
             'group_id': 'None',
             'category_id': 2500})
        self.canvas.delete("annotation")
        self.draw_annotations()
        self.save_annotations()

    def reload_image(self, event):
        self.load_image()
        self.canvas.delete("annotation")
        self.draw_annotations()

    def load_image(self):
        self.label.config(text=f"{self.current_image_index + 1} / {self.image_count}")

        # get image from file
        image_name = self.image_list[self.current_image_index]
        self.current_image_name = image_name.split('#')[-1]
        self.current_folder = image_name.split('#')[-3]
        image_path = os.path.join(self.images_path, image_name)
        image = Image.open(image_path)
        
        self.scale_factor = self.slider.get()
        self.canvas.config(width=min(int((self.scale_factor+0.1)*image.width), image.width), 
                           height=min(int((self.scale_factor+0.1)*image.height), image.height))
        resized_image = image.resize((int(self.scale_factor*image.width), int(self.scale_factor*image.height)))
        self.photo = ImageTk.PhotoImage(resized_image)

        self.image_object = self.canvas.create_image(resized_image.width/2,
                                                     resized_image.height/2,
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
            self.canvas.delete("annotation")
            self.draw_annotations()

    def next_image(self, event):
        if self.current_image_index < len(self.image_list) - 1:
            self.current_image_index += 1
            self.load_image()
            self.canvas.delete("annotation")
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
            print("Selected property:", selected_property.get())
            curAnnotation['corner_property'][self.active_point // 2] = selected_property.get()
            if curAnnotation['category_id'] == 2000 and corner_num in [1, 2]:
                print("Selected T_or_L:", selected_T_or_L.get())
                curAnnotation['T_or_L'][corner_num - 1] = selected_T_or_L.get()
            if curAnnotation['id'] >= 1000000:
                print("saved group_id:", group_id.get())
                if group_id.get() != 'None':
                    curAnnotation['group_id'] = int(group_id.get())
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

        if curAnnotation['category_id'] == 2000 and corner_num in [1, 2]:
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

        # separator
        separator = tk.Frame(selection_window, height=2, bd=1, relief=tk.SUNKEN)
        separator.pack(fill=tk.X, padx=5, pady=5)
        # group id
        group_id_label = tk.Label(selection_window, text="group_id")
        group_id_label.pack()
        group_id = tk.StringVar(value=curAnnotation['group_id'])
        group_id_entry = tk.Entry(selection_window, textvariable=group_id, width=6)
        group_id_entry.pack()
        if curAnnotation['id'] < 1000000:
            group_id_entry.configure(state='readonly')
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
        if not os.path.exists(self.final_output_path):
            os.makedirs(self.final_output_path)
        for folder_name, annotations in self.folders_with_annotations.items():
            # craete sub folder
            folder_path = os.path.join(self.final_output_path, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            # minus DIFF from all keypoints
            for img_name in annotations:
                for i in range(len(annotations[img_name])):
                    annotations[img_name][i]['keypoints'] = [i - DIFF for i in annotations[img_name][i]['keypoints']]
            # apply changes to old json
            old_json_path = os.path.join(self.json_folder, folder_name, 'result_adjust_order.json')
            if not os.path.exists(old_json_path):
                old_json_path = os.path.join(self.json_folder, folder_name, 'corrected_result.json')
            with open(old_json_path, 'r') as file:
                old_json = json.load(file)
            new_annotations = []
            for l in annotations.values():
                new_annotations += l
            # # test for annotation order
            # print(folder_name, ': ', all(new_annotations[i]['id'] < new_annotations[i+1]['id'] for i in range(len(new_annotations) - 1)))
            old_json['annotations'] = new_annotations

            # export as .json
            json_file_path = os.path.join(folder_path, 'corrected_result.json')
            with open(json_file_path, 'w') as json_file:
                json.dump(old_json, json_file, indent=4)
        
    # def get_image_id(self, image_name, old_json):
    #     for image in old_json['images']:
    #         if image['file_name'] == image_name:
    #             return image['id']

    # def update_old_json(self, annotations, old_json) :
    #     new_json = old_json
    #     k = 0
    #     for img_name in annotations:
    #         for annotation in annotations[img_name]:
    #             for i in range(len(old_json['annotations'])):
    #                 if annotation['id'] == old_json['annotations'][i]['id']:
    #                     print(k)
    #                     k += 1
    #                     break
    #     return new_json

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

def read_images(images_path):
    file_list = os.listdir(images_path)
    image_files = [file for file in file_list if file.endswith(".jpg") or file.endswith(".bmp")]
    image_files = natsorted(image_files)
    return image_files
    
    
    
# image folder
images_path = "JSON/haitian_12800/line_error_found"
# file displaying current image annotations
annotations_path = "annotations.txt"
# file recording 
# (1) the index of the last accessed image and 
# (2) the next available annotation index
saved_data_path = "saved_data.txt"
# folder recording output json
final_output_path = "results"
# folder containing original JSON 'JSON/haitian_12800'
json_folder = 'results'

# dict(parent_folder_name -> dict(file_name -> list of annotation dicts))
folders_with_annotations = extract_json_files(json_folder)

image_files = read_images(images_path)
root = tk.Tk()
viewer = ImageViewer(root, image_files, images_path, folders_with_annotations, saved_data_path, final_output_path, json_folder)
root.protocol("WM_DELETE_WINDOW", viewer.quit)
root.mainloop()
