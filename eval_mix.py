import os
import cv2
from skimage.metrics import structural_similarity as compare_ssim
import torch
import numpy as np
import lpips
from torch.autograd import Variable

class calpackage(object):
    def __init__(self,mode="all"):
        self.mode = mode
    def call(self, img1, img2):
        loss_fn_alex = lpips.LPIPS(net='alex',verbose=False)
        if torch.cuda.is_available():
            loss_fn_alex = loss_fn_alex.cuda()
            img1 = img1.cuda()
            img2 = img2.cuda()
        lpips_value_alex = loss_fn_alex(img1, img2,normalize=True)
        return lpips_value_alex

def get_metics(img,referimg,mask=None,size=512):
    #img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    #referimg = cv2.resize(referimg, (size, size), interpolation=cv2.INTER_AREA)

    (score, diff) = compare_ssim(referimg, img, win_size=21, full=True, channel_axis=2)
    ssim = score

    img = np.array(img, dtype=np.float64).transpose((2, 0, 1))
    referimg = np.array(referimg, dtype=np.float64).transpose((2, 0, 1))

    img = torch.from_numpy(img)
    referimg = torch.from_numpy(referimg)

    img1 = Variable(img/ 255).unsqueeze(0)
    img2 = Variable(referimg/ 255).unsqueeze(0)
    caltool = calpackage()
    LPIPS_value_alexnetbase = caltool.call(img1.type(torch.FloatTensor),img2.type(torch.FloatTensor))
    LPIPS_value_alex = LPIPS_value_alexnetbase.detach().cpu().numpy().mean()

    loss2 = torch.mean((img / 255. - referimg / 255.) ** 2)

    out_dict = {}
    if mask is not None:
        #mask = cv2.resize(mask, (size, size), interpolation=cv2.INTER_AREA)
        proportion = np.array(mask, dtype=np.float64).mean() / 255
        ssim = ssim - (1-ssim)*(1-proportion)/proportion
        loss2 = loss2/proportion
        LPIPS_value_alex = LPIPS_value_alex/proportion
        psnr = 10 * torch.log(1 / loss2) / torch.log(torch.tensor(10.0))
    else:
        psnr = 10 * torch.log(1 / loss2) / torch.log(torch.tensor(10.0))

    out_dict["ssim"] = ssim
    out_dict["l2"] = loss2
    out_dict["psnr"] = psnr
    out_dict["LPIPS_value_alex"] = LPIPS_value_alex
    return out_dict

# กำหนดวิธีทดสอบและโฟลเดอร์ให้ถูกต้อง
test_methods = ["merged_output"]
test_root = r"D:\Diffusion\mural-image-inpainting\checkpoints"
referpath = r"D:\Diffusion\mural-image-inpainting\checkpoints\test\input"
maskpath = r"D:\Diffusion\mural-image-inpainting\checkpoints\test\mask"

referfiles = os.listdir(referpath)
maskfiles = os.listdir(maskpath)

out_frame = {"ssim":0,"l2":0,"psnr":0,"LPIPS_value_alex":0}
pred_pathlists= {}
out_dicts={}
run_dicts={}

for method in test_methods:
    # ใช้ os.path.join ต่อ path ให้ถูกต้อง
    path = os.path.join(test_root, method)
    pred_pathlists[method] = path
    out_dicts[method] = out_frame.copy()
    run_dicts[method] = {}

show = True

for i, filename in enumerate(referfiles):
    referimg = cv2.imread(os.path.join(referpath, filename))
    mask = cv2.imread(os.path.join(maskpath, filename))
    if referimg is None:
        print(f"Warning: can't read reference image {filename}")
        continue
    if mask is None:
        print(f"Warning: can't read mask image {filename}, continuing without mask")
        mask = None
    for method in test_methods:
        img_path = os.path.join(pred_pathlists[method], filename)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: can't read predicted image {img_path}, skipping")
            continue
        values = get_metics(img, referimg, mask, size=256)
        for key in values.keys():
            out_dicts[method][key] += values[key]
            run_dicts[method][key] = values[key]

    if show:
        print(f"File: {filename}")
        for method in test_methods:
            print(f"iter:{i+1:3} method:{method:12}", end=" ")
            #print(f"  Method: {method}")
            for key in run_dicts[method].keys():
                print(f"{key}:{run_dicts[method][key]:.4f}  ", end="")
                #print(f"    {key}: {run_dicts[method][key]:.4f}")
            #print("-------------------------------------------------")

    print()

for method in test_methods:
    num = len(referfiles)
    ssim = out_dicts[method]["ssim"] / num
    l2 = out_dicts[method]["l2"] / num
    psnr = out_dicts[method]["psnr"] / num
    LPIPS_value_alex = out_dicts[method]["LPIPS_value_alex"] / num

    print(f"total:{num} method:{method:12} l2_loss:{l2:.4f} psnr:{psnr:.4f} ssim:{ssim:.4f} LPIPS_alex:{LPIPS_value_alex:.4f}")
