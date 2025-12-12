#!/usr/bin/python3
# _*_ coding: utf-8 _*_
#
# Copyright (C) 2024 - 2024 heihieyouheihei, Inc. All Rights Reserved
#
# @Time    : 2024/10/15 下午10:28
# @Author  : 单子叶蚕豆_DzyCd
# @File    : test.py
# @IDE     : PyCharm

from nonebot import logger
from nonebot.rule import to_me
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.exception import MatcherException
from nonebot.params import CommandArg
from nonebot.adapters import Bot, Event
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot import require
require("nonebot_plugin_localstore")
from pathlib import Path
import nonebot_plugin_localstore as store
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
import hashlib
__plugin_meta__ = PluginMetadata(
    name="ImageLibrary",
    description="一个共享给所有人的Bot图库",
    usage="""
        ==所有人可用==
        添加[XXX]: 可以向图库中添加XXX关键词视频/图片/文字内容
        来个/来只/来点[XXX]: 抽取图库中XXX关键词下的内容
        XXX后面接@[数字]可以选择词条下的指定内容
        插画[XXX]: 从网络引擎中获取XXX的随机高清图片
        ==管理员可用==
        @bot 启用/禁用XXX: 允许/禁用群内使用某一词条
            * 设定了禁用的词条不再可以从私聊获取
        @bot 删除XXX: 删除某一词条的部分内容
            只删[数字]: 删除关键词下指定的内容
            彻底删除: 删除整个词条
        @bot 图片列表: 查看图库中的所有关键词
        ==Bot主可用==
        @bot 独占/取消独占: 让某个群聊独占/取消独占一个关键词，其他群和私聊不可用
    """,
    type="application",
    homepage="https://github.com/DZYCD/nonebot-plugin-ImageLibrary",
    supported_adapters={"~onebot.v11"},
)
import random
import aiohttp
import json
import os


data_path: Path = store.get_plugin_data_dir()


class DataSetControl:
    def __init__(self, data_path, base_path):
        self.data_file = data_path
        self.base_path = base_path

    def delete_value(self, key: str, value):
        try:
            dic = self.get_dataset()
            del dic[key][value]
            self.save_dataset(dic)
        except:
            return False

    def delete_key(self, key: str):
        dic = self.get_dataset()
        del dic[key]
        self.save_dataset(dic)

    def get_dataset(self):
        with open(os.path.join(self.base_path, self.data_file), 'r', encoding='UTF-8') as f:
            try:
                load_dict = json.load(f)
                return load_dict
            except:
                return {}

    def save_dataset(self, source):
        json_dict = json.dumps(source, indent=2, ensure_ascii=False)
        with open(os.path.join(self.base_path, self.data_file), 'w', encoding='UTF-8') as f:
            f.write(json_dict)

    def search(self, dic: dict, key: str):
        try:
            return dic[key]
        except:
            return False

    def update_value(self, key: str, target: str, value):
        dic = self.get_dataset()
        if not self.search(dic, key):
            dic[key] = {}
        dic[key][target] = value
        self.save_dataset(dic)

    def get_value(self, key: str, target: str):
        dic = self.get_dataset()
        if self.search(dic, key):
            try:
                return dic[key][target]
            except:
                return False
        return False

    def ensure_directory_exists(self, path):
        if not os.path.exists(os.path.join(self.base_path, path)):
            os.mkdir(os.path.join(self.base_path, path))

    def ensure_file_exists(self, path):
        if not os.path.exists(os.path.join(self.base_path, path)):
            with open(os.path.join(self.base_path, path), 'w', encoding='UTF-8')as f:
                if 'json' in path:
                    f.write(json.dumps("{}"))


dataset = DataSetControl("image.json", data_path)

dataset.ensure_directory_exists("library")

dataset.ensure_file_exists("image.json")

image_library_introduce = on_command("关于图库", rule=to_me(), priority=10, block=True)
image_adder = on_command("添加", rule=to_me(), priority=10, block=True)

get_image = on_command("来只", aliases={"来点", "来个"}, priority=10, block=True)
pixiv_image = on_command("插画", priority=10, block=True,permission=SUPERUSER)

image_deleter = on_command("删除", rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER, priority=10,
                           block=True)
image_list = on_command("图片列表", rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER, priority=10,
                        block=True)
open_image_permission = on_command("启用", rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER, priority=10,
                                   block=True)
close_image_permission = on_command("禁用", rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER, priority=10,
                                    block=True)

disown_image_permission = on_command("取消独占", rule=to_me(), permission=SUPERUSER, priority=10,
                                     block=True)
own_image_permission = on_command("独占", rule=to_me(), permission=SUPERUSER, priority=10,
                                  block=True)


async def image_save(path, filename):
    """保存图片并返回SHA256哈希值"""
    img_src = filename
    async with aiohttp.ClientSession() as session:
        async with session.get(img_src) as response:
            content = await response.read()
            
            # 计算SHA256哈希值
            file_hash = hashlib.sha256(content).hexdigest()
            
            with open(os.path.join(data_path, "library", path), 'wb') as file_obj:
                file_obj.write(content)
                
    return os.path.join(data_path, "library", path), file_hash


def calculate_file_hash(file_path):
    """计算本地文件的SHA256哈希值"""
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
            return hashlib.sha256(file_content).hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败: {e}")
        return None


def check_image_validity(file_path):
    """检查图片文件是否有效"""
    try:
        if not os.path.exists(file_path):
            return False, "文件不存在"
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "文件大小为0"
        
        # 检查文件扩展名
        valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.mp4', '.avi', '.mov']
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in valid_extensions:
            return False, f"不支持的文件格式: {file_ext}"
        
        return True, "文件有效"
    except Exception as e:
        return False, f"检查文件时出错: {e}"


def migrate_old_data():
    """迁移旧数据到新格式"""
    try:
        data = dataset.get_dataset()
        migrated = False
        
        for keyword, contents in data.items():
            if keyword == "adding":
                continue
                
            if not isinstance(contents, dict):
                continue
                
            for key, value in contents.items():
                if key in ["using", "ban"]:
                    continue
                    
                # 如果是旧格式的路径字符串，转换为新格式
                if isinstance(value, str) and (value.endswith('.png') or value.endswith('.mp4')):
                    # 检查文件是否存在
                    is_valid, msg = check_image_validity(value)
                    if is_valid:
                        # 计算哈希值
                        file_hash = calculate_file_hash(value)
                        if file_hash:
                            # 转换为新格式
                            new_value = {
                                "path": value,
                                "hash": file_hash,
                                "type": "image" if value.endswith('.png') else "video"
                            }
                            contents[key] = json.dumps(new_value, ensure_ascii=False)
                            migrated = True
                            logger.info(f"迁移旧数据: {keyword} - {key}")
                    else:
                        logger.warning(f"文件无效，跳过迁移: {value} - {msg}")
        
        if migrated:
            dataset.save_dataset(data)
            logger.info("数据迁移完成")
            
    except Exception as e:
        logger.error(f"数据迁移失败: {e}")


# 启动时执行数据迁移
migrate_old_data()


def check_permission(event, key):
    from_info = event.get_session_id()
    group = 'personal'
    if '_' in from_info:
        group = from_info.split('_')[1]
    try:
        ban_list = dataset.get_value(key, "ban").replace("'", '"')
        res_list = json.loads(ban_list)
        if "ALL" in res_list[0]:
            if group in res_list[0]:
                return True
            return False
        if len(res_list) > 0 and group == "personal":
            return False
        for i in res_list:
            if group in i:
                return False
        return True
    except:
        return True


def get_all_image_urls(event):
    """从事件中获取所有图片URL，包括引用消息中的图片"""
    image_urls = []
    
    # 处理当前消息中的图片
    msg = event.get_message()
    for segment in msg:
        if segment.type == 'image':
            image_urls.append(segment.data['url'])
    
    # 处理引用消息中的图片
    if hasattr(event, 'reply') and event.reply:
        reply_msg = event.reply.message
        for segment in reply_msg:
            if segment.type == 'image':
                image_urls.append(segment.data['url'])
    
    return image_urls


def check_duplicate_image(keyword, file_hash):
    """检查图片是否已存在于关键词中"""
    dataset_data = dataset.get_dataset()
    if keyword not in dataset_data:
        return False
    
    keyword_data = dataset_data[keyword]
    for key, value in keyword_data.items():
        if key in ['using', 'ban']:
            continue
            
        # 处理新格式
        if isinstance(value, str):
            try:
                value_dict = json.loads(value)
                if isinstance(value_dict, dict) and value_dict.get('hash') == file_hash:
                    return True
            except:
                # 如果是旧格式的路径，需要计算哈希比较
                if value.endswith(('.png', '.mp4')):
                    existing_hash = calculate_file_hash(value)
                    if existing_hash == file_hash:
                        return True
    return False


@image_library_introduce.handle()
async def _():
    msg = """Image Library 图库
一个 共享 给 所有人 的 资源库

== 所有人 可用 ==
<命令前缀> 添加 [XXX] : 可以 向 图库 中 添加 XXX 关键词 视频 / 图片 / 文字 内容
<命令前缀> 来个 / 来只 / 来点 [XXX] : 抽取 图库 中 XXX 关键词 下 的 内容
XXX 后面 接 @[数字] 可以 选择 词条 下 的 指定 内容
<命令前缀> 插画 [XXX] : 从 网络 引擎 中 获取 XXX 的 随机 高清 图片
== 管理员 可用 ==
@bot <命令前缀> 启用 / 禁用 XXX : 允许 / 禁用 群内 使用 某一 词条
    * 设定 了 禁用 的 词条 不再 可以 从 私聊 获取
@bot <命令前缀> 删除 XXX : 删除 某一 词条 的 部分 内容
     只删 [数字] : 删除 关键词 下 指定 的 内容
     彻底 删除 : 删除 整个 词条
@bot <命令前缀> 图片 列表 : 查看 图库 中 的 所有 关键词
== Bot主 可用 ==
@bot <命令前缀> 独占 / 取消 独占 : 让 某个 群聊 独占 / 取消 独占 一个 关键词 ，其他 群 和 私聊 不 可用

反馈 ： 1143785758"""
    await image_library_introduce.finish(msg)


@own_image_permission.handle()
async def _(event: Event, args: Message = CommandArg()):
    from_info = event.get_session_id()
    key = args.extract_plain_text()
    group = 'personal'
    if '_' in from_info:
        group = from_info.split('_')[1]
    if group == 'personal':
        await own_image_permission.finish("此 功能 仅 可 用于 群聊 ...")
        return
    try:
        ban_list = ["ALL" + group]
        dataset.update_value(key, "ban", str(ban_list))
    except MatcherException:
        raise
    except Exception as e:
        await own_image_permission.finish(f"{key} 词条 不 存在 ...")
    await own_image_permission.finish(f"本群 已 独占 {key} 词条 ...")


@disown_image_permission.handle()
async def _(event: Event, args: Message = CommandArg()):
    from_info = event.get_session_id()
    key = args.extract_plain_text()
    group = 'personal'
    if '_' in from_info:
        group = from_info.split('_')[1]
    if group == 'personal':
        await disown_image_permission.finish("此 功能 仅 可 用于 群聊 ...")
        return
    try:
        ban_list = '[]'
        dataset.update_value(key, "ban", ban_list)
    except MatcherException:
        raise
    except Exception as e:
        await disown_image_permission.finish(f"{key} 词条 不 存在 ...")
    await disown_image_permission.finish(f"已 解除 {key} 词条 的 独占 ...")


@open_image_permission.handle()
async def _(event: Event, args: Message = CommandArg()):
    from_info = event.get_session_id()
    key = args.extract_plain_text()
    group = 'personal'
    if '_' in from_info:
        group = from_info.split('_')[1]
    if group == 'personal':
        await open_image_permission.finish("此 功能 仅 可 用于 群聊 ...")
        return

    ban_list = ""
    try:
        ban_list = dataset.get_value(key, "ban").replace("'", '"')
    except:
        await open_image_permission.finish(f"{key} 词条 不 存在 ...")
    res_list = json.loads(ban_list)
    if len(res_list) == 0:
        await open_image_permission.finish(f"已 启用 本群 的 {key} 词条 ...")
        return

    if "ALL" in res_list[0]:
        await open_image_permission.finish(f"{key} 词条 已 被 独占 ... | 请 联系 bot主 获取 权限 吧 ...")
    for i in range(len(res_list)):
        if group == res_list[i]:
            del res_list[i]
    dataset.update_value(key, "ban", str(res_list))
    await open_image_permission.finish(f"已 启用 本群 的 {key} 词条 ...")


@close_image_permission.handle()
async def _(event: Event, args: Message = CommandArg()):
    from_info = event.get_session_id()
    key = args.extract_plain_text()
    group = 'personal'
    if '_' in from_info:
        group = from_info.split('_')[1]
    if group == 'personal':
        await close_image_permission.finish("此 功能 仅 可 用于 群聊 ...")
        return
    ban_list = ""
    try:
        ban_list = dataset.get_value(key, "ban").replace("'", '"')
    except:
        await close_image_permission.finish(f"{key} 词条 不 存在 ...")
    res_list = json.loads(ban_list)

    if len(res_list) and "ALL" in res_list[0]:
        await close_image_permission.finish(f"{key} 词条 已 被 独占 ... | 请 联系 bot主 获取 权限 吧 ...")
    res_list.append(group)
    dataset.update_value(key, "ban", str(res_list))
    await close_image_permission.finish(f"已 禁用 本群 的 {key} 词条 ...")


async def get_pixiv_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text()
            m = random.choice(json.loads(data))
            return m


@pixiv_image.handle()
async def fetch_pixiv_data(args: Message = CommandArg()):
    url = "https://image.anosu.top/pixiv/json"
    key = args.extract_plain_text()

    url = url + f"?keyword={key}"

    try:
        m = await get_pixiv_image(url)
        msg = "pid : {}\n>>> {}\ntags : {}".format(m["pid"], m["title"], m["tags"])
        await pixiv_image.finish(msg + MessageSegment.image(m["url"]))
    except MatcherException:
        raise
    except:
        await pixiv_image.finish("没 找到 关键 tag ... | 不过 你 可以 尝试 翻译 成 日文 或者 英文 再 试 一次 ...")


@image_adder.handle()
async def _(event: Event, args: Message = CommandArg()):
    name = args.extract_plain_text()
    if not check_permission(event, name):
        await image_adder.finish(f"词条 {name} 被 禁止 使用 ...")
    
    # 检查是否有引用消息中的图片
    image_urls = get_all_image_urls(event)
    
    if image_urls:
        # 如果有图片，直接处理
        await handle_image_addition(event, name, image_urls)
    else:
        # 没有图片，等待用户输入
        dataset.update_value("adding", "target", name)
        await image_adder.pause(f"关键词 为 ： {name} ... | 你 想 添加 什么 图片 内容 ？ | 可以 直接 发送 图片 、 文字 ， 或者 引用 包含 多张 图片 的 消息 ...")


async def handle_image_addition(event: Event, name: str, image_urls: list):
    """处理图片添加逻辑"""
    p = dataset.get_value(name, "using")
    if not p:
        p = 0
        dataset.update_value(name, "ban", "[]")
    
    added_count = 0
    duplicate_count = 0
    failed_count = 0
    
    for idx, img_url in enumerate(image_urls):
        try:
            # 保存图片并获取哈希值
            local_path, file_hash = await image_save(f"{name}{p + idx + 1}.png", img_url)
            
            # 检查文件有效性
            is_valid, validity_msg = check_image_validity(local_path)
            if not is_valid:
                failed_count += 1
                logger.warning(f"图片文件无效: {local_path} - {validity_msg}")
                continue
            
            # 检查是否重复
            if check_duplicate_image(name, file_hash):
                duplicate_count += 1
                logger.info(f"跳过重复图片: {name} - {file_hash}")
                # 删除重复下载的文件
                try:
                    os.remove(local_path)
                except:
                    pass
                continue
            
            # 存储图片信息（包含哈希值）
            image_info = {
                "path": local_path,
                "hash": file_hash,
                "url": img_url,
                "type": "image"
            }
            dataset.update_value(name, str(p + added_count + 1), json.dumps(image_info, ensure_ascii=False))
            added_count += 1
            
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            failed_count += 1
            continue
    
    # 更新计数器
    if added_count > 0:
        dataset.update_value(name, "using", p + added_count)
    
    # 返回结果
    result_msg = f"关键词 '{name}' 添加 完成 ..."
    if added_count > 0:
        result_msg += f" | 成功 添加 了 {added_count} 张 图片 ..."
    if duplicate_count > 0:
        result_msg += f" | 跳过 了 {duplicate_count} 张 重复 图片 ..."
    if failed_count > 0:
        result_msg += f" | {failed_count} 张 图片 添加 失败 ..."
    
    await image_adder.finish(result_msg)


@image_adder.handle()
async def _(event: Event, bot: Bot):
    name = dataset.get_value("adding", "target")
    
    # 获取所有图片URL
    image_urls = get_all_image_urls(event)
    
    if image_urls:
        # 处理图片
        await handle_image_addition(event, name, image_urls)
    else:
        # 处理文本和视频内容
        msg_text = str(event.get_message())
        msg_text = msg_text.replace("&#91;", "[")
        msg_text = msg_text.replace("&#93;", "]")
        msg_text = msg_text.replace("&amp;", "&")
        
        p = dataset.get_value(name, "using")
        
        if "cn:443/" in msg_text:
            # 视频内容
            local_path = await image_save(f"{name}{p + 1}.mp4", msg_text.split("url=")[1].split(']')[0])
            # 检查文件有效性
            is_valid, validity_msg = check_image_validity(local_path)
            if not is_valid:
                await image_adder.finish(f"视频 文件 无效 ... | {validity_msg}")
                return
            content_info = {
                "path": local_path,
                "type": "video"
            }
        elif "download?" in msg_text:
            # 图片URL
            local_path, file_hash = await image_save(f"{name}{p + 1}.png", msg_text.split("url=")[1].split(']')[0])
            # 检查文件有效性
            is_valid, validity_msg = check_image_validity(local_path)
            if not is_valid:
                await image_adder.finish(f"图片 文件 无效 ... | {validity_msg}")
                return
            content_info = {
                "path": local_path,
                "hash": file_hash,
                "type": "image"
            }
        else:
            # 文本内容
            content_info = {
                "text": msg_text,
                "type": "text"
            }
            local_path = msg_text
        
        if not p:
            dataset.update_value(name, "using", 1)
            dataset.update_value(name, "ban", "[]")
            dataset.update_value(name, "1", json.dumps(content_info, ensure_ascii=False))
        else:
            dataset.update_value(name, "using", p + 1)
            dataset.update_value(name, str(p + 1), json.dumps(content_info, ensure_ascii=False))
        
        await image_adder.finish("添加 成功 ...")


def parse_content_info(content_info_str):
    """解析内容信息，兼容新旧格式"""
    if not content_info_str or content_info_str == 'False':
        return None, "内容不存在"
    
    # 尝试解析为新格式
    try:
        content_info = json.loads(content_info_str)
        if isinstance(content_info, dict):
            return content_info, "新格式"
    except:
        pass
    
    # 如果是旧格式的路径
    if isinstance(content_info_str, str) and (content_info_str.endswith('.png') or content_info_str.endswith('.mp4')):
        # 检查文件有效性
        is_valid, validity_msg = check_image_validity(content_info_str)
        if not is_valid:
            return None, f"文件无效: {validity_msg}"
        
        # 转换为新格式
        file_hash = calculate_file_hash(content_info_str)
        content_type = "image" if content_info_str.endswith('.png') else "video"
        
        content_info = {
            "path": content_info_str,
            "hash": file_hash,
            "type": content_type
        }
        return content_info, "旧格式转换"
    
    # 如果是纯文本
    return {"text": content_info_str, "type": "text"}, "文本格式"


@get_image.handle()
async def _(event: Event, args: Message = CommandArg()):
    msg = args.extract_plain_text()

    if not check_permission(event, msg):
        await get_image.finish(f"词条 {msg} 被 禁止 使用 ...")

    code = 0
    try:
        if '@' in msg:
            code = msg.split("@")[1]
            try:
                int(code)
            except:
                await get_image.finish("@ 后面 需要 跟 一个 数字 ...")
            msg = msg.split("@")[0]
        else:
            p = dataset.get_value(msg, "using")
            if type(p) is bool:
                await get_image.finish("TA 貌似 还 没有 被 添加 ...")
            if int(p) == 0:
                await get_image.finish("关键词 存在 ，但是 关键词 下面 没有 可用 词条 欸 ... | 是不是 被 删除 了 ？")
            code = str(random.randint(1, 100000) % int(p) + 1)

        p = dataset.get_value(msg, "using")
        if type(p) is bool:
            await get_image.finish("TA 貌似 还 没有 被 添加 ...")
        if int(p) == 0:
            await get_image.finish("关键词 存在 ，但是 关键词 下面 没有 可用 词条 欸 ... | 是不是 被 删除 了 ？")
        if int(code) < 1 or int(p) < int(code):
            await get_image.finish(f"标号 不对 哦 ... | 现在 此 关键词 下 只有 {p} 个 条目 ...")

        content_info_str = str(dataset.get_value(msg, code))
        
        # 解析内容信息
        content_info, format_type = parse_content_info(content_info_str)
        
        if not content_info:
            await get_image.finish(f"这个 条目 好像 有问题 ... | {format_type}")
        
        # 如果是文件类型，检查文件有效性
        if content_info.get("type") in ["image", "video"]:
            is_valid, validity_msg = check_image_validity(content_info["path"])
            if not is_valid:
                # 文件无效，删除该条目
                del_value(msg, code)
                left = dataset.get_value(msg, "using")
                await get_image.finish(f'这个 {content_info["type"]} 好像 损坏 了 ... | 我 已经 删除 了 这个 条目 ... | 现在 还有 {left} 个 条目 ...')
        
        # 根据类型发送内容
        content_type = content_info.get("type", "unknown")
        
        if content_type == "image":
            out_msg = content_info["path"]
            logger.success("获取 图片 文件 : {}".format(out_msg))
            await get_image.finish(MessageSegment.image(out_msg))
        elif content_type == "video":
            out_msg = content_info["path"]
            logger.success("获取 视频 文件 : {}".format(out_msg))
            await get_image.finish(MessageSegment.video(out_msg))
        elif content_type == "text":
            out_msg = content_info["text"]
            logger.success("获取 文本 : {}".format(out_msg))
            await get_image.finish(MessageSegment.text(out_msg))
        else:
            await get_image.finish("未知 的 内容 类型 ...")
                
    except MatcherException:
        raise
    except Exception as e:
        logger.error(f"获取 内容 失败 : {e}")
        await get_image.finish("获取 内容 失败 ... | 请 稍后 重试 ... | 图库\n可能 的 错误 类型 ：\n" + "- 网络 连接 问题\n" + "- 文件 损坏\n" + "- 系统 错误\n")


@image_deleter.handle()
async def _(event: Event, args: Message = CommandArg()):
    name = args.extract_plain_text()

    if not check_permission(event, name):
        await image_deleter.finish(f"词条 {name} 被 禁止 使用 ...")
    else:
        dataset.update_value("deleting", "target", name)
        left = dataset.get_value(name, "using")
        if not left:
            await image_deleter.finish(f"词条 不 存在 ...")
        await image_deleter.pause(f"{name} 词条 总共 有 {left} 个 内容 ... | 确定 删除 吗 ？")


def del_value(key, value):
    dataset.delete_value(key, value)
    node = dataset.get_dataset()[key]
    new_dic = {}
    count = 0
    for i in node:
        if i == "using":
            new_dic[i] = node[i] - 1
        elif i == "ban":
            new_dic[i] = node[i]
        else:
            count += 1
            new_dic[count] = node[i]
    dataset.delete_key(key)
    for i in new_dic:
        dataset.update_value(key, i, new_dic[i])


@image_deleter.handle()
async def _(event: Event):
    msg = str(event.get_message())
    if msg == "确定":
        name = dataset.get_value("deleting", "target")
        dataset.update_value(name, "using", 0)
        await image_deleter.finish("删除 成功 ...")
    elif msg == "彻底删除":
        name = dataset.get_value("deleting", "target")
        dataset.delete_key(name)
        await image_deleter.finish("它 已经 不 复 存在 了 ...")
    elif "只删" in msg:
        p = msg.split('只删')[1]
        name = dataset.get_value("deleting", "target")
        del_value(name, p)
        left = dataset.get_value(name, "using")
        await image_deleter.finish(f"好 啦 ， 我 只 删除 了 {p} ... | 现在 应该 还有 {left} 个 条目 ...")
    else:
        await image_deleter.finish("好 吧 ... | 如果 你 确定 好 了 ， 告诉 我 一声 ...")


@image_list.handle()
async def _():
    try:
        note = dataset.get_dataset()
        title_list = []
        for i in note:
            title_list.append(i)
        if "adding" in title_list:
            title_list.remove("adding")
        msg = MessageSegment.text("Bot 总共 记录 了 {} 个 关键词 ... | 分别 为 ：".format(len(title_list)) + "\n" + str(title_list))
        await image_list.finish(msg)
    except MatcherException:
        raise
    except:
        await image_list.finish("出 错 了 ... | 图库\n可能 的 错误 类型 ：\n" + "- 获取 图片 列表 超时\n" + "- 数据 文件 损坏\n")
