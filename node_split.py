import json
import os
import torch
import numpy as np
from PIL import Image, ImageSequence, ImageOps
import folder_paths
VideoReader = None
try:
    from comfy.video_reader import VideoReader
except ImportError:
    pass
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PARAM_JSON_PATH = os.path.join(CUR_DIR, "param.json")
with open(PARAM_JSON_PATH, "r", encoding="utf-8") as f:
    ALL_API_CFG = json.load(f)
SKIP_VAR_SET = {"param1","param2","param3","param4","param5"}


def is_template_placeholder(s: str) -> bool:
    """判断字符串是否为API模板占位符 ###{{[[xxx]]}}###"""
    if not isinstance(s, str):
        return False
    s_strip = s.strip()
    return s_strip.startswith("###{{[[") and s_strip.endswith("]]}}###")


# ==============================================================================
# 附加公共参数节点：param1~param5
# ==============================================================================
class Huis_CommonParamAttach:
    CATEGORY = "绘世玩家/API批量预制工具"
    NAME = "绘世玩家_公共参数附加"
    DISPLAY_NAME = "绘世玩家-公共参数附加(param1~param5)"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("param1", "param2", "param3", "param4", "param5")
    FUNCTION = "pass_common"
    OUTPUT_NODE = True
    @classmethod
    def INPUT_TYPES(cls):
        req = {}
        opt = {}
        common_params = [
            ("param1", "【通用参数1】"),
            ("param2", "【通用参数2】"),
            ("param3", "【通用参数3】"),
            ("param4", "【通用参数4】"),
            ("param5", "【通用参数5】"),
        ]
        for var, label_cn in common_params:
            label_key = f"{var}_label"
            box_key = f"{var}_box"
            # label只读文本放required（仅展示）
            req[label_key] = ("STRING", {
                "default": f"{label_cn} ({var})",
                "readonly": True,
                "multiline": False
            })
            # 实际输入框放到optional，不再强制必填，消除missing报错
            opt[box_key] = ("STRING", {
                "default": f"###{{{{[[{var}]]}}}}###",
                "multiline": False,
                "tooltip": "API通用占位符，导出JSON使用；运行工作流时代表null/不传参"
            })
        return {"required": req, "optional": opt}

    def pass_common(self, **kwargs):
        def get_val(k):
            return kwargs.get(k, f"###{{{{[[{k.replace('_box','')}]]}}}}###")
        return (
            get_val("param1_box"),
            get_val("param2_box"),
            get_val("param3_box"),
            get_val("param4_box"),
            get_val("param5_box"),
        )

# ==============================================================================
# 工厂函数：过滤 param1‑param5，label放在required，输入框放到optional
# ==============================================================================
def create_api_param_node(api_key: str, display_name: str, class_name: str):
    cfg_data = ALL_API_CFG[api_key]
    var_list = []
    raw_item_list = []
    for raw_label, _ in cfg_data.items():
        var_name = raw_label.split("【")[0] if "【" in raw_label else raw_label
        if var_name in SKIP_VAR_SET:
            continue
        var_list.append(var_name)
        raw_item_list.append(raw_label)
    ret_types = tuple(["STRING"] * len(var_list))
    ret_names = tuple(var_list)
    class APINode:
        CATEGORY = "绘世玩家/API批量预制工具"
        NAME = class_name
        DISPLAY_NAME = display_name
        RETURN_TYPES = ret_types
        RETURN_NAMES = ret_names
        FUNCTION = "forward"
        OUTPUT_NODE = True
        @classmethod
        def INPUT_TYPES(cls):
            req = {}
            opt = {}
            for raw_label in raw_item_list:
                var_name = raw_label.split("【")[0] if "【" in raw_label else raw_label
                default_placeholder = f"###{{{{[[{var_name}]]}}}}###"
                if "【" in raw_label and "】" in raw_label:
                    desc_cn = raw_label.split("【")[1].replace("】", "")
                    show_label = f"【{desc_cn}】({var_name})"
                else:
                    show_label = f"{raw_label}"
                label_k = f"{var_name}_label"
                box_k = f"{var_name}_box"
                # 只读标签放required
                req[label_k] = ("STRING", {
                    "default": show_label,
                    "readonly": True,
                    "multiline": False
                })
                # 参数输入框放到optional，消除 Required input is missing 报错
                opt[box_k] = ("STRING", {
                    "default": default_placeholder,
                    "multiline": False,
                    "tooltip": f"API字段 {var_name} 占位符；导出JSON使用；运行工作流代表null/不传参"
                })
            return {"required": req, "optional": opt}

        def forward(self, **kwargs):
            outs = []
            for var in var_list:
                box_k = f"{var}_box"
                # optional不传时，回退为占位符字符串
                val = kwargs.get(box_k, f"###{{{{[[{var}]]}}}}###")
                outs.append(val)
            return tuple(outs)
    return APINode

# ==============================================================================
# 11个独立API参数节点
# ==============================================================================
Table_Text2Img = create_api_param_node(
    api_key="文生图",
    display_name="绘世玩家-参数表：文生图",
    class_name="绘世玩家_参数表_文生图"
)
Table_SingleImgEdit = create_api_param_node(
    api_key="单图编辑",
    display_name="绘世玩家-参数表：单图编辑",
    class_name="绘世玩家_参数表_单图编辑"
)
Table_DoubleImgEdit = create_api_param_node(
    api_key="双图编辑",
    display_name="绘世玩家-参数表：双图编辑",
    class_name="绘世玩家_参数表_双图编辑"
)
Table_ThreeImgEdit = create_api_param_node(
    api_key="三图编辑",
    display_name="绘世玩家-参数表：三图编辑",
    class_name="绘世玩家_参数表_三图编辑"
)
Table_Text2Video = create_api_param_node(
    api_key="文生视频",
    display_name="绘世玩家-参数表：文生视频",
    class_name="绘世玩家_参数表_文生视频"
)
Table_Img2Video = create_api_param_node(
    api_key="图生视频",
    display_name="绘世玩家-参数表：图生视频",
    class_name="绘世玩家_参数表_图生视频"
)
Table_DoubleFrameVideo = create_api_param_node(
    api_key="双图|首尾帧",
    display_name="绘世玩家-参数表：双图|首尾帧",
    class_name="绘世玩家_参数表_双图首尾帧"
)
Table_VideoRef = create_api_param_node(
    api_key="视频参考",
    display_name="绘世玩家-参数表：视频参考",
    class_name="绘世玩家_参数表_视频参考"
)
Table_VideoEdit = create_api_param_node(
    api_key="视频编辑",
    display_name="绘世玩家-参数表：视频编辑",
    class_name="绘世玩家_参数表_视频编辑"
)
Table_AudioGen = create_api_param_node(
    api_key="音频生成",
    display_name="绘世玩家-参数表：音频生成",
    class_name="绘世玩家_参数表_音频生成"
)
Table_ThreeImgRef = create_api_param_node(
    api_key="三图参考",
    display_name="绘世玩家-参数表：三图参考",
    class_name="绘世玩家_参数表_三图参考"
)

# ==============================================================================
# 通用占位符输出节点
# ==============================================================================
class Huis_PlaceholderOutput:
    CATEGORY = "绘世玩家/API批量预制工具"
    NAME = "绘世玩家_通用占位符输出"
    DISPLAY_NAME = "绘世玩家-通用占位符输出"
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "原始输入": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": """
1.模板占位符：###{{[[xxx]]}}### → 运行返回None（代表null/不传），导出JSON识别为null
2.普通文本：masterpiece
3.整数：1024
4.小数：7.5
输出端口为通配类型，可以连接任意节点输入
"""
                }),
                "导出字段类型": (["string", "int", "float"], {
                    "default": "string",
                    "tooltip": "仅导出脚本读取，标记API字段类型，运行不影响输出"
                })
            }
        }
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("任意输出",)
    FUNCTION = "run"
    def run(self, 原始输入, 导出字段类型):
        raw = str(原始输入).strip()
        if is_template_placeholder(raw):
            return (None,)

        val = raw
        try:
            val = int(raw)
        except ValueError:
            try:
                val = float(raw)
            except ValueError:
                val = raw
        return (val,)

# ==============================================================================
# 加载图片节点
# ==============================================================================
class Huis_LoadImageByName:
    CATEGORY = "绘世玩家/API批量预制工具"
    NAME = "绘世玩家_按名称加载图片"
    DISPLAY_NAME = "绘世玩家-按文件名加载图片(Input目录)"
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图片文件名": ("STRING", {
                    "default": "test.png",
                    "multiline": False,
                    "tooltip": "填写ComfyUI input目录下图片完整文件名，如 girl.jpg / frame.png"
                })
            }
        }
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("图片", "遮罩")
    FUNCTION = "load_image_by_name"
    def load_image_by_name(self, 图片文件名):
        input_dir = folder_paths.get_input_directory()
        file_name = str(图片文件名).strip()
        img_path = os.path.join(input_dir, file_name)
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"图片不存在！完整路径：{img_path}\n请确认文件放在ComfyUI input文件夹内")
        img = Image.open(img_path)
        output_images = []
        output_masks = []
        base_w, base_h = None, None
        for frame in ImageSequence.Iterator(img):
            frame = ImageOps.exif_transpose(frame)
            if frame.mode == 'I':
                frame = frame.point(lambda i: i * (1 / 255))
            rgb_frame = frame.convert("RGB")
            curr_w, curr_h = rgb_frame.size
            if base_w is None and base_h is None:
                base_w, base_h = curr_w, curr_h
            if curr_w != base_w or curr_h != base_h:
                continue
            img_np = np.array(rgb_frame).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_np).unsqueeze(0)
            output_images.append(img_tensor)
            if "A" in frame.getbands():
                alpha_np = np.array(frame.getchannel("A")).astype(np.float32) / 255.0
                mask_tensor = torch.from_numpy(alpha_np)
            else:
                mask_tensor = torch.zeros((base_h, base_w), dtype=torch.float32)
            output_masks.append(mask_tensor.unsqueeze(0))
        batch_img = torch.cat(output_images, dim=0)
        batch_mask = torch.cat(output_masks, dim=0)
        img.close()
        return (batch_img, batch_mask)

# ==============================================================================
# 加载视频节点
# ==============================================================================
class Huis_LoadVideoByName:
    CATEGORY = "绘世玩家/API批量预制工具"
    NAME = "绘世玩家_按名称加载视频"
    DISPLAY_NAME = "绘世玩家-按文件名加载视频(Input目录)"
    @classmethod
    def INPUT_TYPES(cls):
        tip_text = """填写input目录下视频完整文件名
本节点仅输出视频路径字符串；
如需接入【裁剪视频(时间)、获取视频元素】，请安装VideoHelperSuite插件，
串联 VHS → Load Video Path 节点中转，中转后再送入视频处理节点"""
        return {
            "required": {
                "视频文件名": ("STRING", {
                    "default": "video.mp4",
                    "multiline": False,
                    "tooltip": tip_text
                })
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("视频文件路径",)
    FUNCTION = "load_video_by_name"
    def load_video_by_name(self, 视频文件名):
        input_dir = folder_paths.get_input_directory()
        file_name = str(视频文件名).strip()
        vid_path = os.path.join(input_dir, file_name)
        if not os.path.exists(vid_path):
            raise FileNotFoundError(f"视频不存在！完整路径：{vid_path}\n请确认文件放在ComfyUI input文件夹内")
        return (vid_path,)

# ==============================================================================
# 加载音频节点
# ==============================================================================
class Huis_LoadAudioByName:
    CATEGORY = "绘世玩家/API批量预制工具"
    NAME = "绘世玩家_按名称加载音频"
    DISPLAY_NAME = "绘世玩家-按文件名加载音频(Input目录)"
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "音频文件名": ("STRING", {
                    "default": "bgm.wav",
                    "multiline": False,
                    "tooltip": "仅输出音频文件路径字符串，只能连接音频合成/混音节点，禁止接入视频裁剪、获取视频元素等视频类节点！"
                })
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("音频文件路径",)
    FUNCTION = "load_audio_by_name"
    def load_audio_by_name(self, 音频文件名):
        input_dir = folder_paths.get_input_directory()
        file_name = str(音频文件名).strip()
        aud_path = os.path.join(input_dir, file_name)
        if not os.path.exists(aud_path):
            raise FileNotFoundError(f"音频不存在！完整路径：{aud_path}\n请确认文件放在ComfyUI input文件夹内")
        return (aud_path,)

# ==============================================================================
# 节点映射表
# ==============================================================================
NODE_CLASS_MAPPINGS = {
    "绘世玩家_公共参数附加": Huis_CommonParamAttach,
    "绘世玩家_参数表_文生图": Table_Text2Img,
    "绘世玩家_参数表_单图编辑": Table_SingleImgEdit,
    "绘世玩家_参数表_双图编辑": Table_DoubleImgEdit,
    "绘世玩家_参数表_三图编辑": Table_ThreeImgEdit,
    "绘世玩家_参数表_文生视频": Table_Text2Video,
    "绘世玩家_参数表_图生视频": Table_Img2Video,
    "绘世玩家_参数表_双图首尾帧": Table_DoubleFrameVideo,
    "绘世玩家_参数表_视频参考": Table_VideoRef,
    "绘世玩家_参数表_视频编辑": Table_VideoEdit,
    "绘世玩家_参数表_音频生成": Table_AudioGen,
    "绘世玩家_参数表_三图参考": Table_ThreeImgRef,
    "绘世玩家_通用占位符输出": Huis_PlaceholderOutput,
    "绘世玩家_按名称加载图片": Huis_LoadImageByName,
    "绘世玩家_按名称加载视频": Huis_LoadVideoByName,
    "绘世玩家_按名称加载音频": Huis_LoadAudioByName,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "绘世玩家_公共参数附加": "绘世玩家-公共参数附加(param1~param5)",
    "绘世玩家_参数表_文生图": "绘世玩家-参数表：文生图",
    "绘世玩家_参数表_单图编辑": "绘世玩家-参数表：单图编辑",
    "绘世玩家_参数表_双图编辑": "绘世玩家-参数表：双图编辑",
    "绘世玩家_参数表_三图编辑": "绘世玩家-参数表：三图参考",
    "绘世玩家_参数表_文生视频": "绘世玩家-参数表：文生视频",
    "绘世玩家_参数表_图生视频": "绘世玩家-参数表：图生视频",
    "绘世玩家_参数表_双图首尾帧": "绘世玩家-参数表：双图|首尾帧",
    "绘世玩家_参数表_视频参考": "绘世玩家-参数表：视频参考",
    "绘世玩家_参数表_视频编辑": "绘世玩家-参数表：视频编辑",
    "绘世玩家_参数表_音频生成": "绘世玩家-参数表：音频生成",
    "绘世玩家_参数表_三图参考": "绘世玩家-参数表：三图参考",
    "绘世玩家_通用占位符输出": "绘世玩家-通用占位符输出",
    "绘世玩家_按名称加载图片": "绘世玩家-按文件名加载图片(Input目录)",
    "绘世玩家_按名称加载视频": "绘世玩家-按文件名加载视频(Input目录)",
    "绘世玩家_按名称加载音频": "绘世玩家-按文件名加载音频(Input目录)",
}