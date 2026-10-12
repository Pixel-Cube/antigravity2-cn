import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

SIGNATURE_START = '/* --- ANTIGRAVITY CHINESE LOCALIZATION START --- */'
SIGNATURE_END = '/* --- ANTIGRAVITY CHINESE LOCALIZATION END --- */'

BRAND_TITLE_ALIASES = {
    'english': 'english',
    'en': 'english',
    'default': 'english',
    'hidden': 'hidden',
    'hide': 'hidden',
    'none': 'hidden',
    'translated': 'translated',
    'chinese': 'translated',
    'cn': 'translated',
    'zh': 'translated',
}


def get_option_value(name, default_value):
  args = sys.argv[1:]
  for i, arg in enumerate(args):
    if arg == name and i + 1 < len(args):
      return args[i + 1]
    if arg.startswith(name + '='):
      return arg[len(name) + 1 :]
  return default_value


USE_TW = '--tw' in sys.argv
DICTS_FOLDER = 'dicts_tw' if USE_TW else 'dicts'
BRAND_TITLE_MODE = BRAND_TITLE_ALIASES.get(
    str(get_option_value('--brand-title', 'english')).lower(), 'english'
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_text(text):
  if not text:
    return ''
  text = re.sub(r'\s+', ' ', text).strip()
  text = (
      text.replace('’', "'")
      .replace('‘', "'")
      .replace('“', '"')
      .replace('”', '"')
      .replace('…', '...')
  )
  return text


def load_dictionary():
  total_map = {}
  dicts_dir = os.path.join(BASE_DIR, DICTS_FOLDER)
  if os.path.isdir(dicts_dir):
    for fname in sorted(os.listdir(dicts_dir)):
      if fname.endswith('.json'):
        fpath = os.path.join(dicts_dir, fname)
        try:
          with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
          for k, v in data.items():
            norm_k = normalize_text(k)
            if norm_k:
              total_map[norm_k] = v
        except Exception:
          pass
  if BRAND_TITLE_MODE == 'english':
    total_map.pop(normalize_text('Antigravity'), None)
  elif BRAND_TITLE_MODE == 'hidden':
    total_map[normalize_text('Antigravity')] = ''
  return total_map


def extract_js_template_from_engine():
  """Extract the exact browser preload injection JS from localization_engine.js."""
  engine_js_path = os.path.join(BASE_DIR, 'localization_engine.js')
  with open(engine_js_path, 'r', encoding='utf-8') as f:
    src = f.read()
  start_marker = 'const jsSource = `${SIGNATURE_START}\n'
  end_marker = '\n${SIGNATURE_END}`;'
  s_idx = src.find(start_marker)
  e_idx = src.find(end_marker)
  if s_idx == -1 or e_idx == -1:
    # Try CRLF
    start_marker = 'const jsSource = `${SIGNATURE_START}\r\n'
    end_marker = '\r\n${SIGNATURE_END}`;'
    s_idx = src.find(start_marker)
    e_idx = src.find(end_marker)
  if s_idx == -1 or e_idx == -1:
    raise RuntimeError(
        'Could not locate jsSource template in localization_engine.js'
    )

  raw_tpl = src[s_idx + len(start_marker) : e_idx]
  # In JS template literal, \\ was used to produce a single \ in the generated JS string
  unescaped_tpl = raw_tpl.replace('\\\\', '\\').replace('\\`', '`')
  unescaped_tpl = unescaped_tpl.replace(
      '${USE_TW ? "true" : "false"}', 'true' if USE_TW else 'false'
  )
  return f'{SIGNATURE_START}\n{unescaped_tpl}\n{SIGNATURE_END}'


def generate_js():
  full_dict = load_dictionary()
  long_entries = sorted(
      full_dict.items(), key=lambda item: len(item[0]), reverse=True
  )
  dict_json = json.dumps(full_dict, ensure_ascii=False, indent=4)
  entries_json = json.dumps(long_entries, ensure_ascii=False)

  js_source = extract_js_template_from_engine()
  return js_source.replace('DICT_PLACEHOLDER', dict_json).replace(
      'REPLACEMENT_ENTRIES_PLACEHOLDER', entries_json
  )


def clean_preload_js(content):
  pattern = re.compile(
      re.escape(SIGNATURE_START) + r'[\s\S]*?' + re.escape(SIGNATURE_END)
  )
  return pattern.sub('', content)


def clean_menu_js(content):
  start_mark = '// =========================================='
  end_mark = 'translateMenu(menu.items);'
  s_idx = content.find(start_mark)
  e_idx = content.find(end_mark)
  if s_idx != -1 and e_idx != -1 and s_idx < e_idx:
    return content[:s_idx] + content[e_idx + len(end_mark) :]
  return content


def clean_tray_js(content):
  content = re.sub(
      r'\n\s*\/\* --- TRAY TRANSLATION START --- \*\/[\s\S]*?\/\* --- TRAY'
      r' TRANSLATION END --- \*\/',
      '',
      content,
  )
  content = re.sub(
      r'\n\s*\/\* --- TRAY DOUBLE CLICK START --- \*\/[\s\S]*?\/\* --- TRAY'
      r' DOUBLE CLICK END --- \*\/',
      '',
      content,
  )
  return content


def patch_menu_js(menu_content):
  menu_cleaned = clean_menu_js(menu_content)
  translations_obj = (
      """{
        'File': '檔案', 'Edit': '編輯', 'View': '檢視', 'Window': '視窗', 'Help': '說明',
        'New Window': '開新視窗', 'Create Project': '建立專案', 'Command Palette': '命令選擇區',
        'Docs': '說明文件', 'Check for Updates': '檢查更新', 'Toggle Developer Tools': '切換開發人員工具',
        'Undo': '復原', 'Redo': '重做', 'Cut': '剪下', 'Copy': '複製', 'Paste': '貼上', 'Select All': '全選',
        'Minimize': '最小化', 'Maximize': '最大化', 'Close': '關閉', 'Zoom': '縮放', 'Reset Zoom': '重設縮放',
        'Zoom In': '放大', 'Zoom Out': '縮小', 'Toggle Full Screen': '切換全螢幕',
        'Toggle Between Light/Dark Themes': '切換淺色/深色佈景主題', 'Split Terminal': '分割終端機',
        'Split Conversation Horizontally': '水平分割對話', 'Split Conversation Vertically': '垂直分割對話',
        'Split': '分割', 'Split Right': '向右分割', 'Split Down': '向下分割', 'Replace With New': '替換為新對話',
        'Show in File Explorer': '在檔案總管中顯示', 'Reveal in Finder': '在 Finder 中顯示',
        'Find in conversation': '在對話中尋找', 'Version': '版本'
    }"""
      if USE_TW
      else """{
        'File': '文件', 'Edit': '编辑', 'View': '视图', 'Window': '窗口', 'Help': '帮助',
        'New Window': '新建窗口', 'Create Project': '创建项目', 'Command Palette': '命令面板',
        'Docs': '文档', 'Check for Updates': '检查更新', 'Toggle Developer Tools': '切换开发者工具',
        'Undo': '撤销', 'Redo': '重做', 'Cut': '剪切', 'Copy': '复制', 'Paste': '粘贴', 'Select All': '全选',
        'Minimize': '最小化', 'Maximize': '最大化', 'Close': '关闭', 'Zoom': '缩放', 'Reset Zoom': '重置缩放',
        'Zoom In': '放大', 'Zoom Out': '缩小', 'Toggle Full Screen': '切换全屏',
        'Toggle Between Light/Dark Themes': '切换浅色/深色主题', 'Split Terminal': '拆分终端',
        'Split Conversation Horizontally': '水平拆分会话', 'Split Conversation Vertically': '垂直拆分会话',
        'Split': '拆分', 'Split Right': '向右拆分', 'Split Down': '向下拆分', 'Replace With New': '替换为新会话',
        'Show in File Explorer': '在文件资源管理器中显示', 'Reveal in Finder': '在访达中显示',
        'Find in conversation': '在会话中查找', 'Version': '版本'
    }"""
  )
  menu_translation_js = f"""
    // ==========================================
    // Antigravity Native Menu Chinese Translation
    // ==========================================
    const translations = {translations_obj};
    function translateMenu(items) {{
        for (const item of items) {{
            let label = item.label || '';
            let mnemonic = '';
            let cleanLabel = label;
            const m = label.match(/&([a-zA-Z])/);
            if (m) {{
                mnemonic = "(&" + m[1] + ")";
                cleanLabel = label.replace('&', '');
            }}
            if (translations[cleanLabel]) {{
                item.label = translations[cleanLabel] + mnemonic;
            }} else if (translations[label]) {{
                item.label = translations[label];
            }} else if (/^Version\\s*([\\d\\.]*)$/i.test(cleanLabel)) {{
                item.label = cleanLabel.replace(/^Version\\s*([\\d\\.]*)$/i, (match, v) => v ? "版本 " + v : "版本");
            }}
            if (item.submenu && item.submenu.items) {{
                translateMenu(item.submenu.items);
            }}
        }}
    }}
    translateMenu(menu.items);
    """
  target_str = 'electron_1.Menu.setApplicationMenu(menu);'
  idx = menu_cleaned.find(target_str)
  if idx != -1:
    return (
        menu_cleaned[:idx] + menu_translation_js + '\n    ' + menu_cleaned[idx:]
    ), True
  return menu_cleaned, False


def patch_tray_js(tray_content):
  tray_cleaned = clean_tray_js(tray_content)
  use_tw_js = 'true' if USE_TW else 'false'
  trans_obj = (
      "{ 'No agents running': '無執行中的代理', 'Open Antigravity': '開啟"
      " Antigravity', 'Quit': '結束' }"
      if USE_TW
      else (
          "{ 'No agents running': '无运行中的智能体', 'Open Antigravity': '打开"
          " Antigravity', 'Quit': '退出' }"
      )
  )

  def repl_create(m):
    args = m.group(1)
    return f"""function createTray({args}) {{
    /* --- TRAY TRANSLATION START --- */
    const USE_TW = {use_tw_js};
    const translations = {trans_obj};
    for (const item of actions) {{
        if (!item || !item.label) continue;
        if (translations[item.label]) {{
            item.label = translations[item.label];
        }} else if (item.label.startsWith('Open ')) {{
            item.label = (USE_TW ? '開啟 ' : '打开 ') + item.label.slice(5);
        }} else if (item.label === 'Quit') {{
            item.label = USE_TW ? '結束' : '退出';
        }}
    }}
    /* --- TRAY TRANSLATION END --- */"""

  tray_patched, n1 = re.subn(
      r'function\s+createTray\s*\(([^)]*)\)\s*\{',
      repl_create,
      tray_cleaned,
      count=1,
  )

  dbl_click_replacement = """tray.setContextMenu(contextMenu);
    /* --- TRAY DOUBLE CLICK START --- */
    const openAction = actions.find(item => item && typeof item.click === 'function' && !['Quit', '退出', '結束'].includes(item.label));
    if (openAction) {
        tray.on('double-click', () => {
            const wins = electron_1.BrowserWindow.getAllWindows();
            if (wins.length > 0 && wins[0].isMinimized()) {
                wins[0].restore();
            }
            openAction.click();
        });
    }
    /* --- TRAY DOUBLE CLICK END --- */"""
  tray_patched = tray_patched.replace(
      'tray.setContextMenu(contextMenu);', dbl_click_replacement, 1
  )

  replacement_count = (
      "countItem.label = count > 0 ? `${count} 個代理執行中` : '無執行中的代理';"
      if USE_TW
      else (
          'countItem.label = count > 0 ? `${count} 个智能体运行中` :'
          " '无运行中的智能体';"
      )
  )
  tray_patched = re.sub(
      r"countItem\.label\s*=\s*\([\s\S]*?' running';",
      replacement_count,
      tray_patched,
  )
  return tray_patched, (n1 > 0)


def patch_loading_js(loading_content):
  replacement_text = (
      '<div class="text">正在載入 Antigravity…</div>'
      if USE_TW
      else '<div class="text">正在加载 Antigravity…</div>'
  )
  for old in [
      '<div class="text">Loading Antigravity</div>',
      '<div class="text">反重力引擎已啟動，正在努力擺脫地心引力...</div>',
      '<div class="text">反重力引擎已启动，正在努力摆脱地心引力...</div>',
  ]:
    loading_content = loading_content.replace(old, replacement_text)
  return loading_content


def patch_updater_js(updater_content):
  target_options = """                title: 'Check for Updates',
                message: 'No updates available',
                buttons: ['OK'],"""
  replacement_options = (
      """                title: '檢查更新',
                message: '目前沒有可用的更新',
                buttons: ['好'],"""
      if USE_TW
      else """                title: '检查更新',
                message: '暂无可用更新',
                buttons: ['确定'],"""
  )
  return updater_content.replace(target_options, replacement_options)


def compute_integrity(data_bytes):
  block_size = 4 * 1024 * 1024
  full_hash = hashlib.sha256(data_bytes).hexdigest()
  blocks = []
  if len(data_bytes) == 0:
    blocks.append(hashlib.sha256(b'').hexdigest())
  else:
    for i in range(0, len(data_bytes), block_size):
      blocks.append(hashlib.sha256(data_bytes[i : i + block_size]).hexdigest())
  return {
      'algorithm': 'SHA256',
      'hash': full_hash,
      'blockSize': block_size,
      'blocks': blocks,
  }


def build_localized_asar(src_asar_path, dst_asar_path):
  with open(src_asar_path, 'rb') as f:
    raw = f.read()

  _, header_size, _, json_len = struct.unpack('<IIII', raw[:16])
  header = json.loads(raw[16 : 16 + json_len].decode('utf-8'))
  data_offset = 8 + header_size

  dist_files = header['files']['dist']['files']

  def read_dist_text(name):
    info = dist_files[name]
    off = data_offset + int(info['offset'])
    sz = info['size']
    return raw[off : off + sz].decode('utf-8')

  print('[修改] 正在向 preload.js 注入汉化代码...')
  preload_new = (
      clean_preload_js(read_dist_text('preload.js')) + '\n' + generate_js()
  )
  print(
      '[修改] preload.js 注入成功！(词库已加载'
      f' {len(load_dictionary())} 条翻译词条)'
  )

  patched_map = {
      ('dist', 'preload.js'): preload_new.encode('utf-8'),
  }

  if 'menu.js' in dist_files:
    print('[修改] 正在向 menu.js 注入顶部系统菜单汉化...')
    menu_new, ok = patch_menu_js(read_dist_text('menu.js'))
    patched_map[('dist', 'menu.js')] = menu_new.encode('utf-8')
    if ok:
      print('[修改] 顶部菜单汉化注入成功！')

  if 'tray.js' in dist_files:
    print('[修改] 正在向 tray.js 注入系统托盘右键菜单汉化...')
    tray_new, ok = patch_tray_js(read_dist_text('tray.js'))
    patched_map[('dist', 'tray.js')] = tray_new.encode('utf-8')
    if ok:
      print('[修改] 系统托盘菜单汉化注入成功！')

  if 'loadingOverlay.js' in dist_files:
    print('[修改] 正在向 loadingOverlay.js 注入启动加载页汉化...')
    loading_new = patch_loading_js(read_dist_text('loadingOverlay.js'))
    patched_map[('dist', 'loadingOverlay.js')] = loading_new.encode('utf-8')
    print('[修改] 启动加载页汉化注入成功！')

  if 'updater.js' in dist_files:
    print('[修改] 正在向 updater.js 注入检查更新弹窗汉化...')
    updater_new = patch_updater_js(read_dist_text('updater.js'))
    patched_map[('dist', 'updater.js')] = updater_new.encode('utf-8')
    print('[修改] 检查更新弹窗汉化注入成功！')

  # Traverse header tree and rebuild payload sequentially
  payload_chunks = []
  current_offset = 0

  def walk_node(node, path_tuple):
    nonlocal current_offset
    if 'files' in node:
      for name, child in node['files'].items():
        walk_node(child, path_tuple + (name,))
    elif 'offset' in node and not node.get('unpacked', False):
      if path_tuple in patched_map:
        file_bytes = patched_map[path_tuple]
      else:
        old_off = data_offset + int(node['offset'])
        old_sz = node['size']
        file_bytes = raw[old_off : old_off + old_sz]
      node['offset'] = str(current_offset)
      node['size'] = len(file_bytes)
      if 'integrity' in node:
        node['integrity'] = compute_integrity(file_bytes)
      payload_chunks.append(file_bytes)
      current_offset += len(file_bytes)

  walk_node(header, ())

  new_json_bytes = json.dumps(
      header, ensure_ascii=False, separators=(',', ':')
  ).encode('utf-8')
  new_json_len = len(new_json_bytes)
  aligned_json_len = (new_json_len + 3) & ~3
  padding_len = aligned_json_len - new_json_len
  new_pickle2_size = 4 + aligned_json_len
  new_header_size = 4 + new_pickle2_size

  header_prefix = struct.pack(
      '<IIII', 4, new_header_size, new_pickle2_size, new_json_len
  )
  with open(dst_asar_path, 'wb') as f:
    f.write(header_prefix)
    f.write(new_json_bytes)
    if padding_len > 0:
      f.write(b'\x00' * padding_len)
    for chunk in payload_chunks:
      f.write(chunk)

  print(
      f'[打包] 已成功生成汉化版 ASAR 包: {dst_asar_path}'
      f' ({os.path.getsize(dst_asar_path) / (1024*1024):.2f} MB)'
  )


def detect_install_dir():
  manual_dir = get_option_value('--install-dir', '')
  if manual_dir and os.path.exists(manual_dir):
    return os.path.abspath(manual_dir)
  local_appdata = os.environ.get('LOCALAPPDATA', '')
  candidates = [
      os.path.join(local_appdata, 'Programs', 'Antigravity'),
      os.path.join(local_appdata, 'Programs', 'antigravity'),
      r'C:\Program Files\Antigravity',
      r'D:\Programs\Antigravity',
      r'D:\Antigravity',
  ]
  for c in candidates:
    if c and os.path.exists(os.path.join(c, 'resources', 'app.asar')):
      return os.path.abspath(c)
  raise RuntimeError('未能自动找到 Antigravity 安装目录，请检查安装路径。')


def check_app_running():
  res = subprocess.run(
      ['tasklist', '/fi', 'imagename eq Antigravity.exe', '/nh'],
      capture_output=True,
      text=True,
      encoding='utf-8',
      errors='ignore',
  )
  return 'antigravity.exe' in res.stdout.lower()


def close_app():
  print('[1] 正在关闭 Antigravity 2.0 客户端以解除文件锁定...')
  subprocess.run(
      ['taskkill', '/f', '/im', 'Antigravity.exe', '/t'], capture_output=True
  )
  time.sleep(1.5)


def clean_electron_cache():
  appdata = os.environ.get('APPDATA', '')
  if not appdata:
    return
  support_dir = os.path.join(appdata, 'Antigravity')
  if not os.path.isdir(support_dir):
    return
  cleaned = 0
  for c in [
      'Cache',
      'Code Cache',
      'GPUCache',
      'DawnWebGPUCache',
      'DawnGraphiteCache',
  ]:
    p = os.path.join(support_dir, c)
    if os.path.isdir(p):
      shutil.rmtree(p, ignore_errors=True)
      cleaned += 1
  if cleaned:
    print(f'[缓存] 已清理 {cleaned} 个 Electron 缓存目录。')


def main():
  install_dir = detect_install_dir()
  resources_dir = (
      install_dir
      if os.path.exists(os.path.join(install_dir, 'app.asar'))
      else os.path.join(install_dir, 'resources')
  )
  asar_path = os.path.join(resources_dir, 'app.asar')
  bak_path = os.path.join(resources_dir, 'app.asar.bak')
  prebuilt_path = os.path.join(BASE_DIR, 'app.asar.cn')

  if '--prebuild' in sys.argv:
    print(f'====== 正在预构建 Antigravity 2.0 中文汉化包 (无需关闭软件) ======')
    src = bak_path if os.path.exists(bak_path) else asar_path
    build_localized_asar(src, prebuilt_path)
    if not os.path.exists(bak_path):
      with open(asar_path, 'rb') as f:
        is_loc = SIGNATURE_START.encode('utf-8') in f.read()
      if not is_loc:
        shutil.copy2(asar_path, bak_path)
        print(f'[备份] 已提前创建官方原版备份: {bak_path}')
    print('[√] 预构建与官方备份全部就绪！')
    return

  was_running = check_app_running()
  if '--no-kill' not in sys.argv and was_running:
    close_app()

  if '--huifu' in sys.argv:
    print('====== 正在卸载中文汉化，恢复官方原版 ======')
    if not os.path.exists(bak_path):
      print('[!] 未找到备份文件 app.asar.bak，可能尚未安装过汉化。')
      sys.exit(1)
    shutil.copy2(bak_path, asar_path)
    os.remove(bak_path)
    clean_electron_cache()
    print('[√] 官方英文原版 app.asar 已成功恢复！')
  else:
    print('====== 正在安装 Antigravity 2.0 中文汉化 ======')
    with open(asar_path, 'rb') as f:
      is_loc = SIGNATURE_START.encode('utf-8') in f.read()
    if not is_loc:
      print(f'[备份] 正在创建官方原始包备份: {bak_path} ...')
      shutil.copy2(asar_path, bak_path)
    src_for_build = bak_path if os.path.exists(bak_path) else asar_path
    tmp_out = os.path.join(BASE_DIR, 'app.asar.tmp')
    build_localized_asar(src_for_build, tmp_out)
    shutil.move(tmp_out, asar_path)
    clean_electron_cache()
    print('[√] Antigravity 2.0 汉化部署完成！')

  if was_running and '--no-kill' not in sys.argv:
    exe_path = os.path.join(install_dir, 'Antigravity.exe')
    if os.path.exists(exe_path):
      print('[启动] 正在重新启动 Antigravity 2.0 客户端...')
      subprocess.Popen(
          [exe_path],
          creationflags=subprocess.DETACHED_PROCESS
          | subprocess.CREATE_NEW_PROCESS_GROUP,
      )


if __name__ == '__main__':
  main()
