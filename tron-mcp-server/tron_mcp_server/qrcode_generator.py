"""QR Code 生成模块 — 将 TRON 钱包地址生成二维码图片"""

import os
import qrcode
from qrcode.image.pil import PilImage


def generate_address_qrcode(
    address: str,
    output_dir: str = None,
    filename: str = None,
    box_size: int = 10,
    border: int = 4,
) -> dict:
    """
    将 TRON 钱包地址生成 QR Code PNG 图片并保存到本地。

    Args:
        address: TRON 钱包地址（将被编码到二维码中）
        output_dir: 输出目录，默认为当前工作目录下的 qrcodes 文件夹
        filename: 文件名（不含扩展名），默认为 qr_{address}.png
        box_size: 二维码每个格子的像素大小，默认 10
        border: 二维码边框宽度（格子数），默认 4

    Returns:
        包含 file_path, address, file_size 的结果字典
    """
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "qrcodes")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 设置文件名
    if filename is None:
        # 用地址的前8位和后6位作为文件名，避免文件名过长
        filename = f"qr_{address[:8]}_{address[-6:]}"
    
    file_path = os.path.join(output_dir, f"{filename}.png")

    # 生成 QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(address)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    return {
        "file_path": file_path,
        "address": address,
        "file_size": file_size,
    }
