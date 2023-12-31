import json
import os

DIFF = 150

def extract_annotations(json_path):
    with open(json_path, 'r') as file:
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
        new_dict['keypoints'] = [i + DIFF for i in d['keypoints']]
        new_dict['corner_property'] = d['corner_property']
        new_dict['category'] = categories[d['category_id']]
        if new_dict['category'] == "parking_space":
            new_dict['T_or_L'] = d['T_or_L']
            new_dict['parking_slot_property_1'] = d['parking_slot_property_1']

        image_name = images[d['image_id']]
        annotations[image_name].append(new_dict)
    
    return annotations # dict(file_name -> list of annotation dicts)

def extract_json_files(folder_path):
    json_files = {}
    for root, dirs, files, in os.walk(folder_path):
        if files:
            for file in files:
                if file == 'result_adjust_order.json' or file == 'corrected_result.json':
                    path = os.path.join(root, file)
                    root = root.split('/')[-1]
                    json_files[root] = extract_annotations(path)
    # dict(parent_folder_name -> dict(file_name -> list of annotation dicts))
    return json_files
