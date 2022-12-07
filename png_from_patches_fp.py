
import os
import glob
import h5py
from tqdm import tqdm
import openslide
from concurrent.futures import ProcessPoolExecutor

def main(slide_file_path,patch_coord_path,png_path,target_size=0):

    wsi = openslide.open_slide(slide_file_path)
        

    with h5py.File(patch_coord_path,'r') as hdf5_file:
        coords = hdf5_file['coords']
        patch_level = hdf5_file['coords'].attrs['patch_level']
        patch_size = hdf5_file['coords'].attrs['patch_size']
        length = len(coords)
        if target_size > 0:
            target_patch_size = (target_size, ) * 2

        else:
            target_patch_size = None

        for coord_id in range(length):
        
            img = wsi.read_region(coords[coord_id], patch_level, (patch_size, patch_size)).convert('RGB')

            if target_patch_size is not None:
                img = img.resize(target_patch_size)

            img.save(os.path.join(png_path,str(coord_id)+'.png'))



if __name__ == '__main__':
    num_proc=12
    pool = ProcessPoolExecutor(num_proc)

    target_size = 512
    patch_coords_path = 'GBM_all_case_coords/patches_coords'  # patch坐标信息
    wsi_path = 'GBM_50_case_svs/'# svs病理图路径
    save_png_path = '/patch_to_png'
    
    

    for idx in tqdm(os.listdir(patch_coords_path)):
        patch_coord_path = os.path.join(patch_coords_path,idx)
        slide_file_path = glob.glob(os.path.join(wsi_path,"*",idx.replace('.h5','.svs')))
        if len(slide_file_path)==0:
            continue
        slide_file_path = slide_file_path[0]
        png_path = os.path.join(save_png_path,idx.replace('.h5',''))
        if not os.path.exists(png_path):
            os.makedirs(png_path)

        pool.submit(main,slide_file_path,patch_coord_path,png_path,target_size=target_size)

    pool.shutdown(wait=True)
    print('end')
    
