"""Build, configure and execute the 5 sequential notebooks for ASD-EASE WESAD pipeline."""
from pathlib import Path
import json
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS_DIR = ROOT / "ai/notebooks"

def create_cell(cell_type, source):
    if isinstance(source, list):
        source = "".join(source)
    if cell_type == "markdown":
        return nbformat.v4.new_markdown_cell(source)
    else:
        return nbformat.v4.new_code_cell(source)

# ==============================================================================
# NOTEBOOK 01: Chuẩn hóa & Khám phá Dữ liệu WESAD
# ==============================================================================
def build_nb01():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        create_cell("markdown", [
            "# 01. Chuẩn hóa dữ liệu WESAD\n",
            "\n",
            "- Chuyển đổi các thông số cảm biến thô từ WESAD thành các đại lượng chuẩn cùng với dự án"
        ]),
        create_cell("code", [
            "from pathlib import Path\n",
            "import sys, json\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "pd.set_option('display.max_colwidth', None)\n",
            "here = Path.cwd().resolve()\n",
            "ROOT = next((p for p in [here, *here.parents] if (p / 'ai/requirements.txt').is_file() and (p / 'backend').is_dir()), None)\n",
            "if ROOT is None:\n",
            "    raise RuntimeError('Vui lòng mở notebook trong repository ASD-EASE')\n",
            "sys.path.insert(0, str(ROOT / 'ai'))\n",
            "\n",
            "DATA_DIR = ROOT / 'ai/data/interim/wesad/normalized-v1'\n",
            "print('Thư mục dữ liệu chuẩn hóa:', DATA_DIR)"
        ]),
        create_cell("markdown", [
            "## 1. Bảng chuẩn hóa thông số cảm biến\n",
            "\n",
            "- Đối chiếu giữa tín hiệu gốc của WESAD và thông số chuẩn được dùng trong dự án."
        ]),
        create_cell("code", [
            "sensor_conversion = [\n",
            "    {\n",
            "        'Cảm biến': 'ACC',\n",
            "        'Tín hiệu gốc WESAD': 'Số đếm thô 32 Hz (±2g / 64)',\n",
            "        'Hành động': 'Đổi từ số đếm sang m/s² và tính độ lớn vector',\n",
            "        'Kết quả dùng cho Dự án': 'Gia tốc chuẩn m/s² & Độ lớn cử động tay'\n",
            "    },\n",
            "    {\n",
            "        'Cảm biến': 'BVP',\n",
            "        'Tín hiệu gốc WESAD': 'Sóng quang thể tích 64 Hz (a.u.)',\n",
            "        'Hành động': 'Chạy thuật toán bvp-causal-peaks đổi từ sóng quang (a.u.) sang nhịp tim (bpm)',\n",
            "        'Kết quả dùng cho Dự án': 'Nhịp tim HR (bpm, 40 - 200 bpm)'\n",
            "    },\n",
            "    {\n",
            "        'Cảm biến': 'Labels',\n",
            "        'Tín hiệu gốc WESAD': '8 mã thực nghiệm (0 đến 7)',\n",
            "        'Hành động': 'Gom từ 8 mã (0-7) sang nhãn nhị phân: 0 (Bình thường), 1 (Stress)',\n",
            "        'Kết quả dùng cho Dự án': '0: Bình thường / 1: Stress'\n",
            "    },\n",
            "    {\n",
            "        'Cảm biến': 'EDA',\n",
            "        'Tín hiệu gốc WESAD': 'Tín hiệu da 4 Hz (µS) trong file .pkl',\n",
            "        'Hành động': 'Giữ nguyên đơn vị µS, lọc bỏ mẫu lỗi NaN/Inf và đồng bộ thời gian',\n",
            "        'Kết quả dùng cho Dự án': 'Tín hiệu EDA sạch (µS)'\n",
            "    }\n",
            "]\n",
            "\n",
            "pd.set_option('display.max_colwidth', None)\n",
            "df_conversion = pd.DataFrame(sensor_conversion)\n",
            "display(df_conversion)"
        ]),
        create_cell("markdown", [
            "## 2. Tổng quan 15 đối tượng sau chuẩn hóa\n",
            "\n",
            "- Thống kê thời lượng ghi nhận (phút) và số lượng mẫu của các kênh tín hiệu từ `S2` đến `S17`."
        ]),
        create_cell("code", [
            "recordings_file = DATA_DIR / 'recordings.jsonl'\n",
            "rows = []\n",
            "with open(recordings_file, 'r', encoding='utf-8') as f:\n",
            "    for line in f:\n",
            "        meta = json.loads(line)\n",
            "        sub = meta['subject_id']\n",
            "        sub_meta = json.loads((DATA_DIR / meta['metadata']).read_text(encoding='utf-8'))\n",
            "        bvp_count = sub_meta['channels']['bvp']['count']\n",
            "        duration_min = (bvp_count / 64) / 60\n",
            "        rows.append({\n",
            "            'Đối tượng': sub,\n",
            "            'Thời lượng (phút)': round(duration_min, 1),\n",
            "            'BVP (64Hz)': bvp_count,\n",
            "            'EDA (4Hz)': sub_meta['channels']['eda_us']['count'],\n",
            "            'ACC (32Hz)': sub_meta['channels']['acc_norm_ms2']['count']\n",
            "        })\n",
            "\n",
            "df_subjects = pd.DataFrame(rows)\n",
            "display(df_subjects)\n",
            "print(f'Tổng thời lượng đo của 15 người: {df_subjects[\"Thời lượng (phút)\"].sum():.1f} phút (~{df_subjects[\"Thời lượng (phút)\"].sum()/60:.1f} giờ)')"
        ]),
        create_cell("markdown", [
            "## 3. Phân bố dữ liệu theo nhãn 0 và 1\n",
            "\n",
            "- Đối chiếu giữa các mã trạng thái gốc của WESAD và 2 nhãn chuẩn hóa đưa vào huấn luyện AI."
        ]),
        create_cell("code", [
            "verif_file = DATA_DIR / 'verification.json'\n",
            "verif = json.loads(verif_file.read_text(encoding='utf-8'))\n",
            "\n",
            "label_config = [\n",
            "    {'Mã WESAD': '1', 'Trạng thái gốc': 'Baseline (Nghỉ ngơi)', 'Chuẩn hóa thành': 'Nhãn 0 (Bình thường)', 'Đưa vào train AI': 'Có', 'Màu': '#3498DB'},\n",
            "    {'Mã WESAD': '2', 'Trạng thái gốc': 'Stress (Căng thẳng)', 'Chuẩn hóa thành': 'Nhãn 1 (Stress)', 'Đưa vào train AI': 'Có', 'Màu': '#E74C3C'},\n",
            "    {'Mã WESAD': '3', 'Trạng thái gốc': 'Amusement (Thư giãn)', 'Chuẩn hóa thành': 'Loại trừ', 'Đưa vào train AI': 'Không', 'Màu': '#BDC3C7'},\n",
            "    {'Mã WESAD': '4', 'Trạng thái gốc': 'Meditation (Thiền)', 'Chuẩn hóa thành': 'Loại trừ', 'Đưa vào train AI': 'Không', 'Màu': '#BDC3C7'},\n",
            "    {'Mã WESAD': '0, 5, 6, 7', 'Trạng thái gốc': 'Đệm, nghỉ phụ & khảo sát', 'Chuẩn hóa thành': 'Loại trừ', 'Đưa vào train AI': 'Không', 'Màu': '#95A5A6'}\n",
            "]\n",
            "\n",
            "rows = []\n",
            "for cfg in label_config:\n",
            "    code = cfg['Mã WESAD']\n",
            "    if code == '0, 5, 6, 7':\n",
            "        other_wins = sum(verif['label_coverage'][c]['windows'] for c in ['0', '5', '6', '7', 'mixed'] if c in verif['label_coverage'])\n",
            "        dur_min = round(other_wins / 60, 1)\n",
            "    else:\n",
            "        wins = verif['label_coverage'][code]['windows']\n",
            "        dur_min = round(wins / 60, 1)\n",
            "    rows.append({**cfg, 'Thời lượng (phút)': dur_min})\n",
            "\n",
            "df_labels = pd.DataFrame(rows)\n",
            "\n",
            "# Trực quan hóa 2 góc nhìn: Toàn bộ mã gốc WESAD vs 2 nhãn train AI\n",
            "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))\n",
            "\n",
            "# Đồ thị 1: Toàn bộ mã gốc WESAD (Cột xám = Bị loại trừ)\n",
            "bars = ax1.bar(df_labels['Trạng thái gốc'], df_labels['Thời lượng (phút)'], color=df_labels['Màu'], width=0.55)\n",
            "ax1.set_ylabel('Thời lượng (phút)', fontsize=10)\n",
            "ax1.set_title('Phân bố thời lượng theo mã gốc WESAD\\n(Cột xám = Bị loại trừ, không đưa vào train AI)', fontsize=11, pad=10)\n",
            "ax1.tick_params(axis='x', rotation=15)\n",
            "for bar in bars:\n",
            "    y = bar.get_height()\n",
            "    ax1.text(bar.get_x() + bar.get_width()/2.0, y + 8, f'{y:.1f}p', ha='center', va='bottom', fontweight='bold', fontsize=9)\n",
            "ax1.set_ylim(0, max(df_labels['Thời lượng (phút)']) * 1.15)\n",
            "ax1.grid(axis='y', linestyle='--', alpha=0.4)\n",
            "\n",
            "# Đồ thị 2: Tỷ lệ 2 nhãn chuẩn hóa đưa vào train AI\n",
            "t_base = df_labels.loc[df_labels['Mã WESAD'] == '1', 'Thời lượng (phút)'].values[0]\n",
            "t_stress = df_labels.loc[df_labels['Mã WESAD'] == '2', 'Thời lượng (phút)'].values[0]\n",
            "train_times = [t_base, t_stress]\n",
            "train_labels = [f'Nhãn 0: Bình thường\\n({t_base}p)', f'Nhãn 1: Stress\\n({t_stress}p)']\n",
            "train_colors = ['#3498DB', '#E74C3C']\n",
            "ax2.pie(train_times, labels=train_labels, colors=train_colors, autopct='%1.1f%%', startangle=90, explode=(0, 0.08),\n",
            "        textprops={'fontsize': 10, 'fontweight': 'bold'}, wedgeprops={'edgecolor': 'white', 'linewidth': 2})\n",
            "ax2.set_title('Tập Huấn luyện AI sau Chuẩn hóa\\n(Bài toán 2 lớp nhị phân: Non-Stress vs Stress)', fontsize=11, pad=10)\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()\n",
            "\n",
            "display(df_labels[['Mã WESAD', 'Trạng thái gốc', 'Chuẩn hóa thành', 'Đưa vào train AI', 'Thời lượng (phút)']])"
        ])
    ]
    return nb

# ==============================================================================
# NOTEBOOK 02: Đánh giá Thuật toán Nhịp tim Cổ tay (HR vs ECG)
# ==============================================================================
def build_nb02():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        create_cell("markdown", [
            "# 02. Đánh giá thuật toán nhịp tim cổ tay của dataset\n",
            "\n",
            "- Dùng máy đo điện tim ngực (ECG) làm **Thước đo chuẩn vàng (Ground Truth)** để chấm điểm thuật toán nhịp tim cổ tay (`bvp-causal-peaks`).\n",
            "- Mục tiêu: Đánh giá sai số (MAE) và kiểm tra xem thuật toán cổ tay có bị mất nhịp khi người dùng bị Stress hay không."
        ]),
        create_cell("code", [
            "from pathlib import Path\n",
            "import sys, json\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "pd.set_option('display.max_colwidth', None)\n",
            "here = Path.cwd().resolve()\n",
            "ROOT = next((p for p in [here, *here.parents] if (p / 'ai/requirements.txt').is_file() and (p / 'backend').is_dir()), None)\n",
            "if ROOT is None:\n",
            "    raise RuntimeError('Vui lòng mở notebook trong repository ASD-EASE')\n",
            "sys.path.insert(0, str(ROOT / 'ai'))\n",
            "\n",
            "REVIEW = ROOT / 'ai/data/interim/wesad/hr-ecg-review-v1'\n",
            "report = json.loads((REVIEW / 'report.json').read_text(encoding='utf-8'))\n",
            "print(f'Trạng thái báo cáo: {report[\"status\"]}, Đủ 15 đối tượng: {report[\"all_15_subjects\"]}')"
        ]),
        create_cell("markdown", [
            "## 1. Độ phủ và sai số theo từng trạng thái\n",
            "\n",
            "- **MAE:** Sai số tuyệt đối trung bình so với chuẩn ECG (dưới 5 bpm là rất tốt); **P90:** 90% số lần đo có sai số nhỏ hơn mức này.\n",
            "- **Phát hiện:** Thuật toán đo ở firmware: bvp-causal-peaks bị mất tới **83,6% dữ liệu ở pha Stress** (độ phủ chỉ còn 16,4%)."
        ]),
        create_cell("code", [
            "label_names = {'1': 'Baseline (Nghỉ ngơi)', '2': 'Stress (Căng thẳng)', '3': 'Amusement (Thư giãn)'}\n",
            "rows = []\n",
            "for label, name in label_names.items():\n",
            "    s = report['pooled']['by_source_label'][label]\n",
            "    rows.append({\n",
            "        'Trạng thái': name,\n",
            "        'Cửa sổ ECG (10s)': s['windows'],\n",
            "        'Cửa sổ đủ HR & ECG (10s)': s['paired_windows'],\n",
            "        'Độ phủ nhịp tim (%)': round(100 * s['paired_coverage_among_reference'], 2),\n",
            "        'MAE (bpm)': round(s['mae_bpm'], 2),\n",
            "        'P90 (bpm)': round(s['p90_absolute_error_bpm'], 2),\n",
            "        'Bias (bpm)': round(s['bias_bpm'], 2)\n",
            "    })\n",
            "\n",
            "df_summary = pd.DataFrame(rows)\n",
            "display(df_summary)\n",
            "\n",
            "# Vẽ biểu đồ cột độ phủ\n",
            "plt.figure(figsize=(7.5, 4))\n",
            "bars = plt.bar(df_summary['Trạng thái'], df_summary['Độ phủ nhịp tim (%)'], color=['#3498DB', '#E74C3C', '#2ECC71'], width=0.5)\n",
            "plt.ylabel('Độ phủ (%)', fontsize=11)\n",
            "plt.ylim(0, 100)\n",
            "plt.title('Độ phủ nhịp tim của thuật toán cũ theo từng trạng thái', fontsize=12, pad=12)\n",
            "for bar in bars:\n",
            "    yval = bar.get_height()\n",
            "    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f'{yval}%', ha='center', va='bottom', fontweight='bold')\n",
            "plt.axhline(50, color='gray', linestyle='--', alpha=0.5)\n",
            "plt.grid(axis='y', linestyle='--', alpha=0.4)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]),
        create_cell("markdown", [
            "## 2. Chi tiết theo từng Đối tượng (15 người)\n",
            "\n",
            "- Thống kê chi tiết MAE và độ phủ trên từng người (`S2` đến `S17`).\n",
            "- Đảm bảo số liệu trung bình phản ánh đúng thực tế, không che giấu ca cá biệt."
        ]),
        create_cell("code", [
            "sub_rows = []\n",
            "for p in report['subject_summaries']:\n",
            "    s = p['binary_task']\n",
            "    sub_rows.append({\n",
            "        'Đối tượng': p['subject'],\n",
            "        'Cửa sổ đủ HR & ECG (10s)': s['paired_windows'],\n",
            "        'Độ phủ nhịp tim (%)': round(100 * s['paired_coverage_among_reference'], 2),\n",
            "        'MAE (bpm)': round(s['mae_bpm'], 2),\n",
            "        'P90 (bpm)': round(s['p90_absolute_error_bpm'], 2)\n",
            "    })\n",
            "\n",
            "df_sub = pd.DataFrame(sub_rows).set_index('Đối tượng')\n",
            "display(df_sub)\n",
            "print(f'Sai số trung bình toàn tập (Macro MAE): {report[\"macro_subject_mae_bpm\"]:.2f} bpm')"
        ]),
        create_cell("markdown", [
            "## 3. Dạng sóng Thực tế & Hiện tượng Mất nhịp (S2)\n",
            "\n",
            "- So sánh sóng điện tim ECG (ngực) và sóng quang BVP (cổ tay) ở pha Stress.\n",
            "- Quan sát trực quan dải thời gian pha Stress (phút 38 đến 48) trên chuỗi 100 phút."
        ]),
        create_cell("code", [
            "SUBJECT = 'S2'\n",
            "with np.load(REVIEW / SUBJECT / 'review_snippets.npz', allow_pickle=False) as snippets:\n",
            "    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(12, 3.5))\n",
            "    ecg = snippets['label2_ecg']\n",
            "    qrs = snippets['label2_qrs']\n",
            "    bvp = snippets['label2_bvp']\n",
            "    \n",
            "    t_ecg = np.arange(len(ecg)) / 700\n",
            "    qidx = np.minimum((qrs * 700).round().astype(int), len(ecg) - 1)\n",
            "    ax_l.plot(t_ecg[:1400], ecg[:1400], color='#2C3E50', lw=1.0)\n",
            "    ax_l.scatter(qrs[qrs < 2.0], ecg[qidx[qrs < 2.0]], color='#E74C3C', s=25, zorder=3)\n",
            "    ax_l.set_title('Sóng ECG ngực ở pha Stress (Đỉnh QRS rõ)', fontsize=11)\n",
            "    ax_l.set_xlabel('Thời gian (giây)')\n",
            "    ax_l.grid(True, linestyle='--', alpha=0.4)\n",
            "    \n",
            "    t_bvp = np.arange(len(bvp)) / 64\n",
            "    ax_r.plot(t_bvp[:128], bvp[:128], color='#E74C3C', lw=1.2)\n",
            "    ax_r.set_title('Sóng BVP cổ tay ở pha Stress (Co mạch làm dẹt)', fontsize=11)\n",
            "    ax_r.set_xlabel('Thời gian (giây)')\n",
            "    ax_r.grid(True, linestyle='--', alpha=0.4)\n",
            "    plt.tight_layout()\n",
            "    plt.show()\n",
            "\n",
            "# Chuỗi thời gian so sánh ECG vs BVP suốt 100 phút\n",
            "pairs = pd.read_csv(REVIEW / SUBJECT / 'comparison.csv')\n",
            "plt.figure(figsize=(12, 3.8))\n",
            "plt.plot(pairs['time_ms'] / 60000, pairs['ecg_hr_bpm'], label='ECG ngực (Chuẩn)', color='#27AE60', lw=1.2, alpha=0.85)\n",
            "plt.plot(pairs['time_ms'] / 60000, pairs['ppg_hr_bpm'], label='BVP cổ tay (Thuật toán cũ)', color='#E74C3C', lw=1.2)\n",
            "# Highlight dải thời gian pha Stress của S2\n",
            "stress_mask = pairs['source_label_code'] == 2\n",
            "t_s_min = pairs.loc[stress_mask, 'time_ms'].min() / 60000\n",
            "t_s_max = pairs.loc[stress_mask, 'time_ms'].max() / 60000\n",
            "plt.axvspan(t_s_min, t_s_max, color='#E74C3C', alpha=0.18, label=f'Pha Stress ({t_s_min:.1f}p - {t_s_max:.1f}p: Mất 97,2% nhịp BVP)')\n",
            "plt.xlabel('Thời gian ghi nhận (phút)', fontsize=10)\n",
            "plt.ylabel('Nhịp tim (bpm)', fontsize=10)\n",
            "plt.title(f'So sánh nhịp tim liên tục suốt buổi đo — {SUBJECT} (Dải hồng: Pha Stress bị đứt nhịp hoàn toàn)', fontsize=11, pad=10)\n",
            "plt.legend(loc='upper right')\n",
            "plt.grid(True, linestyle='--', alpha=0.4)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ])
    ]
    return nb

# ==============================================================================
# NOTEBOOK 03: Đối chiếu Thuật toán PPG Công bố (MSPTD)
# ==============================================================================
def build_nb03():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        create_cell("markdown", [
            "# 03. Đối chiếu Thuật toán PPG Công bố (MSPTD)\n",
            "\n",
            "- Thử nghiệm thuật toán đỉnh đa thang đo (**MSPTDfast v2** của *Peter H. Charlton et al.*).\n",
            "- Mục tiêu: Cứu dữ liệu nhịp tim ở pha Stress so với thuật toán ban đầu.\n",
            "- Dữ liệu đối chiếu được sinh bởi script `scripts/compare_wesad_published_ppg.py`."
        ]),
        create_cell("code", [
            "from pathlib import Path\n",
            "import sys, json\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "pd.set_option('display.max_colwidth', None)\n",
            "here = Path.cwd().resolve()\n",
            "ROOT = next((p for p in [here, *here.parents] if (p / 'ai/requirements.txt').is_file() and (p / 'backend').is_dir()), None)\n",
            "if ROOT is None:\n",
            "    raise RuntimeError('Vui lòng mở notebook trong repository ASD-EASE')\n",
            "sys.path.insert(0, str(ROOT / 'ai'))\n",
            "\n",
            "PUB_REVIEW = ROOT / 'ai/data/interim/wesad/hr-published-review-v1'\n",
            "pub_rep = json.loads((PUB_REVIEW / 'report.json').read_text(encoding='utf-8'))\n",
            "print('Đã tải thành công báo cáo đối chiếu MSPTD trên 15 đối tượng.')"
        ]),
        create_cell("markdown", [
            "## 1. So sánh Độ phủ Nhịp tim (Cứu dữ liệu Pha Stress)\n",
            "\n",
            "- Thuật toán **MSPTD Gated** nâng độ phủ pha Stress từ 16,40% lên **61,73%** (tăng gấp 3,7 lần).\n",
            "- Độ phủ ở các pha Baseline và Amusement cũng tăng trên 81%."
        ]),
        create_cell("code", [
            "pooled = pub_rep['pooled']\n",
            "rows = []\n",
            "cond_labels = [('baseline', 'Baseline (Nghỉ ngơi)'), ('stress', 'Stress (Căng thẳng)'), ('amusement', 'Amusement (Thư giãn)')]\n",
            "\n",
            "for cond_key, cond_name in cond_labels:\n",
            "    c = pooled[cond_key]\n",
            "    cov_old = round(c['old_causal_peaks']['coverage_among_ecg_pct'], 2)\n",
            "    cov_new = round(c['msptd_gated']['coverage_among_ecg_pct'], 2)\n",
            "    rows.append({\n",
            "        'Trạng thái': cond_name,\n",
            "        'Thuật toán cũ (%)': cov_old,\n",
            "        'MSPTD Gated (%)': cov_new,\n",
            "        'Cải thiện (%)': round(cov_new - cov_old, 2)\n",
            "    })\n",
            "\n",
            "df_cov = pd.DataFrame(rows)\n",
            "display(df_cov)\n",
            "\n",
            "# Vẽ biểu đồ so sánh độ phủ trực quan\n",
            "x = np.arange(len(df_cov))\n",
            "width = 0.35\n",
            "\n",
            "fig, ax = plt.subplots(figsize=(8.5, 4.2))\n",
            "rects1 = ax.bar(x - width/2, df_cov['Thuật toán cũ (%)'], width, label='Thuật toán cũ', color='#E74C3C')\n",
            "rects2 = ax.bar(x + width/2, df_cov['MSPTD Gated (%)'], width, label='MSPTD Gated (Mới)', color='#27AE60')\n",
            "\n",
            "ax.set_ylabel('Độ phủ (%)', fontsize=11)\n",
            "ax.set_title('So sánh độ phủ nhịp tim: Thuật toán cũ vs MSPTD Gated', fontsize=12, pad=12)\n",
            "ax.set_xticks(x)\n",
            "ax.set_xticklabels(df_cov['Trạng thái'], fontsize=10)\n",
            "ax.set_ylim(0, 100)\n",
            "ax.legend(loc='upper right')\n",
            "ax.grid(axis='y', linestyle='--', alpha=0.4)\n",
            "\n",
            "for rect in rects1 + rects2:\n",
            "    h = rect.get_height()\n",
            "    ax.annotate(f'{h}%', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),\n",
            "                textcoords='offset points', ha='center', va='bottom', fontsize=9, fontweight='bold')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]),
        create_cell("markdown", [
            "## 2. So sánh Sai số (MAE) trên các Cửa sổ Chung\n",
            "\n",
            "- Kiểm tra sai số trên các cửa sổ cả hai thuật toán cùng tính ra kết quả.\n",
            "- Sai số giữa hai phương pháp là tương đương (~1,6 – 3,3 bpm), giữ nguyên chất lượng đo."
        ]),
        create_cell("code", [
            "mae_rows = []\n",
            "for cond_key, cond_name in cond_labels:\n",
            "    c = pooled[cond_key]\n",
            "    old_m = c['old_causal_peaks']\n",
            "    new_m = c['msptd_gated']\n",
            "    mae_rows.append({\n",
            "        'Trạng thái': cond_name,\n",
            "        'MAE Cũ (bpm)': round(old_m['mae_bpm'], 2),\n",
            "        'MAE MSPTD (bpm)': round(new_m['mae_bpm'], 2),\n",
            "        'P90 Cũ (bpm)': round(old_m['p90_ae_bpm'], 2),\n",
            "        'P90 MSPTD (bpm)': round(new_m['p90_ae_bpm'], 2)\n",
            "    })\n",
            "\n",
            "df_mae = pd.DataFrame(mae_rows)\n",
            "display(df_mae)"
        ]),
        create_cell("markdown", [
            "## 3. Quyết định Đặc trưng (Feature Decision)\n",
            "\n",
            "- **Kết luận:** Chọn **MSPTD Gated** làm thuật toán trích xuất nhịp tim trên tập WESAD.\n",
            "- Bổ sung thêm đặc trưng `hr_is_valid` để mô hình AI biết cửa sổ nào có nhịp tim tin cậy."
        ]),
        create_cell("code", [
            "decision_rows = [\n",
            "    {'Hạng mục': 'Thuật toán Nhịp tim (HR)', 'Quyết định': 'MSPTD Gated (Peter H. Charlton et al.)', 'Lý do': 'Cứu độ phủ pha Stress từ 16,40% lên 61,73% (gấp 3,7 lần), MAE 2,9 bpm', 'Firmware ESP32': 'Giữ nguyên 100%'},\n",
            "    {'Hạng mục': 'Xử lý Mất nhịp', 'Quyết định': 'Bổ sung cờ hr_is_valid (1: hợp lệ, 0: mất nhịp)', 'Lý do': 'Báo hiệu cho AI biết độ tin cậy của nhịp tim ở từng cửa sổ', 'Firmware ESP32': 'Giữ nguyên 100%'},\n",
            "    {'Hạng mục': 'Kiến trúc Triển khai', 'Quyết định': 'Phân tầng: Vòng đeo gửi dữ liệu thô, Server chạy AI', 'Lý do': 'Thuật toán nhẹ trên vòng đeo; Server chạy MSPTD và model phát hiện Stress', 'Firmware ESP32': 'Không đổi code ESP32'}\n",
            "]\n",
            "df_decision = pd.DataFrame(decision_rows)\n",
            "display(df_decision)"
        ])
    ]
    return nb

# ==============================================================================
# NOTEBOOK 04: Trích xuất & Phân tích 36 Đặc trưng Stress
# ==============================================================================
def build_nb04():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        create_cell("markdown", [
            "# 04. Trích xuất & Phân tích 36 Đặc trưng Stress\n",
            "\n",
            "- Cắt các cửa sổ trượt 60 giây (bước nhảy 10 giây) và trích xuất 36 đặc trưng sinh lý.\n",
            "- Tập dữ liệu gồm **3.040 cửa sổ** (904 Stress ~29,7%, 2.136 Non-stress ~70,3%).\n",
            "- Dữ liệu được tạo bởi script `scripts/extract_wesad_features.py`."
        ]),
        create_cell("code", [
            "from pathlib import Path\n",
            "import sys, json\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "pd.set_option('display.max_colwidth', None)\n",
            "here = Path.cwd().resolve()\n",
            "ROOT = next((p for p in [here, *here.parents] if (p / 'ai/requirements.txt').is_file() and (p / 'backend').is_dir()), None)\n",
            "if ROOT is None:\n",
            "    raise RuntimeError('Vui lòng mở notebook trong repository ASD-EASE')\n",
            "sys.path.insert(0, str(ROOT / 'ai'))\n",
            "\n",
            "FEAT_DIR = ROOT / 'ai/data/processed/wesad/features-v1'\n",
            "report = json.loads((FEAT_DIR / 'report.json').read_text(encoding='utf-8'))\n",
            "df = pd.read_csv(FEAT_DIR / 'dataset.csv')\n",
            "\n",
            "print(f'Số lượng cửa sổ: {len(df)}, Số đặc trưng: {report[\"feature_count\"]}')\n",
            "print(f'Tỷ lệ Stress: {report[\"total_stress_windows\"]} ({report[\"stress_prevalence\"]*100:.1f}%), Non-stress: {report[\"total_non_stress_windows\"]}')"
        ]),
        create_cell("markdown", [
            "## 1. Danh mục 36 Đặc trưng Sinh lý\n",
            "\n",
            "- **14 EDA:** Tonic mean/std, Phasic mean/auc, SCR peak count, SCR amplitude...\n",
            "- **13 ACC:** Gia tốc chuẩn mean/std/energy, cường độ chuyển động, các trục x/y/z.\n",
            "- **9 HR:** Nhịp tim mean/std/min/max/slope và các cờ kiểm định hợp lệ."
        ]),
        create_cell("code", [
            "eda_cols = [c for c in report['feature_names'] if c.startswith('eda_')]\n",
            "acc_cols = [c for c in report['feature_names'] if c.startswith('acc_')]\n",
            "hr_cols = [c for c in report['feature_names'] if c.startswith('hr_')]\n",
            "\n",
            "df_group = pd.DataFrame([\n",
            "    {'Cảm biến': 'EDA', 'Số đặc trưng': len(eda_cols), 'Đặc trưng tiêu biểu': ', '.join(eda_cols[:4]) + '...'},\n",
            "    {'Cảm biến': 'ACC', 'Số đặc trưng': len(acc_cols), 'Đặc trưng tiêu biểu': ', '.join(acc_cols[:4]) + '...'},\n",
            "    {'Cảm biến': 'HR', 'Số đặc trưng': len(hr_cols), 'Đặc trưng tiêu biểu': ', '.join(hr_cols[:4]) + '...'}\n",
            "])\n",
            "display(df_group)\n",
            "\n",
            "print('5 dòng dữ liệu mẫu:')\n",
            "display(df[['subject_id', 'label', 'eda_mean', 'eda_phasic_auc', 'acc_motion_intensity', 'hr_mean', 'hr_is_valid']].head())"
        ]),
        create_cell("markdown", [
            "## 2. Phân bố Đặc trưng: Bình thường vs Căng thẳng\n",
            "\n",
            "- So sánh mức biến động của các đặc trưng cốt lõi khi một người rơi vào Stress.\n",
            "- Khi Stress, độ dẫn da (EDA) và nhịp tim (HR) thường tăng cao rõ rệt."
        ]),
        create_cell("code", [
            "features_to_plot = ['eda_mean', 'eda_phasic_auc', 'hr_mean', 'acc_motion_intensity']\n",
            "titles = ['EDA Trung bình (µS)', 'EDA Phasic AUC', 'Nhịp tim HR Trung bình (bpm)', 'Cường độ Chuyển động (ACC)']\n",
            "\n",
            "fig, axes = plt.subplots(2, 2, figsize=(11, 7))\n",
            "axes = axes.flatten()\n",
            "\n",
            "for i, (col, title) in enumerate(zip(features_to_plot, titles)):\n",
            "    data_non_stress = df[df['label'] == 0][col].dropna()\n",
            "    data_stress = df[df['label'] == 1][col].dropna()\n",
            "    \n",
            "    bp = axes[i].boxplot([data_non_stress, data_stress], tick_labels=['Non-Stress', 'Stress'], patch_artist=True, showfliers=False)\n",
            "    bp['boxes'][0].set_facecolor('#3498DB')\n",
            "    bp['boxes'][1].set_facecolor('#E74C3C')\n",
            "    axes[i].set_title(title, fontsize=11)\n",
            "    axes[i].grid(True, linestyle='--', alpha=0.4)\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]),
        create_cell("markdown", [
            "## 3. Độ Tương quan của Đặc trưng với Nhãn Stress\n",
            "\n",
            "- Xếp hạng các đặc trưng có hệ số tương quan tuyến tính mạnh nhất với trạng thái Stress.\n",
            "- Các đặc trưng EDA và HR thể hiện tương quan tích cực rõ nét nhất."
        ]),
        create_cell("code", [
            "corrs = df[report['feature_names']].apply(lambda col: col.corr(df['label']))\n",
            "top_corrs = corrs.abs().sort_values(ascending=False).head(10)\n",
            "top_corrs_signed = corrs[top_corrs.index]\n",
            "\n",
            "plt.figure(figsize=(9, 4.5))\n",
            "colors = ['#E74C3C' if v > 0 else '#3498DB' for v in top_corrs_signed]\n",
            "bars = plt.barh(top_corrs_signed.index, top_corrs_signed.values, color=colors, height=0.6)\n",
            "plt.axvline(0, color='gray', linestyle='--')\n",
            "plt.xlabel('Hệ số tương quan Pearson với nhãn Stress', fontsize=11)\n",
            "plt.title('Top 10 Đặc trưng Tương quan Mạnh nhất với Trạng thái Stress', fontsize=12, pad=12)\n",
            "plt.gca().invert_yaxis()\n",
            "plt.grid(axis='x', linestyle='--', alpha=0.4)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ])
    ]
    return nb

# ==============================================================================
# NOTEBOOK 05: Huấn luyện & Đánh giá Mô hình Stress (LOSO)
# ==============================================================================
def build_nb05():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        create_cell("markdown", [
            "# 05. Huấn luyện & Đánh giá Mô hình Stress (LOSO)\n",
            "\n",
            "- Đánh giá kiểm thử chéo 15 người (**Leave-One-Subject-Out - LOSO**) để kiểm tra độ khái quát hóa trên người chưa từng thấy.\n",
            "- So sánh Dummy Classifier, Logistic Regression và Random Forest.\n",
            "- Dữ liệu đánh giá được sinh bởi script `scripts/train_wesad_baseline.py`."
        ]),
        create_cell("code", [
            "from pathlib import Path\n",
            "import sys, json\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "pd.set_option('display.max_colwidth', None)\n",
            "here = Path.cwd().resolve()\n",
            "ROOT = next((p for p in [here, *here.parents] if (p / 'ai/requirements.txt').is_file() and (p / 'backend').is_dir()), None)\n",
            "if ROOT is None:\n",
            "    raise RuntimeError('Vui lòng mở notebook trong repository ASD-EASE')\n",
            "sys.path.insert(0, str(ROOT / 'ai'))\n",
            "\n",
            "MODEL_DIR = ROOT / 'ai/models/wesad-baseline-v1'\n",
            "rep = json.loads((MODEL_DIR / 'report.json').read_text(encoding='utf-8'))\n",
            "print(f'Báo cáo LOSO hoàn tất: {rep[\"status\"]}, Tổng cửa sổ: {rep[\"total_windows\"]}, Số đối tượng: {rep[\"total_subjects\"]}')"
        ]),
        create_cell("markdown", [
            "## 1. Bảng so sánh Hiệu năng các Mô hình\n",
            "\n",
            "- So sánh Accuracy, Macro F1 và Stress F1 qua kiểm thử LOSO 15 fold.\n",
            "- **Logistic Regression** đạt hiệu năng ấn tượng nhất: **Accuracy 89,74%**, **Macro F1 87,95%**, **Stress F1 83,30%**."
        ]),
        create_cell("code", [
            "model_keys = [\n",
            "    ('RandomForest_ACC_only', 'Random Forest (Chỉ ACC)'),\n",
            "    ('RandomForest_EDA_only', 'Random Forest (Chỉ EDA)'),\n",
            "    ('RandomForest_EDA_and_ACC', 'Random Forest (EDA + ACC)'),\n",
            "    ('RandomForest_Full_Multimodal', 'Random Forest (EDA + ACC + HR)'),\n",
            "    ('HistGradientBoosting_Full_Multimodal', 'HistGradientBoosting (EDA + ACC + HR)'),\n",
            "    ('LogisticRegression_Full_Multimodal', 'Logistic Regression (EDA + ACC + HR)')\n",
            "]\n",
            "\n",
            "summary_rows = []\n",
            "for key, name in model_keys:\n",
            "    if key in rep['models']:\n",
            "        ov = rep['models'][key]['overall']\n",
            "        summary_rows.append({\n",
            "            'Mô hình': name,\n",
            "            'Accuracy (%)': round(ov['accuracy'] * 100, 2),\n",
            "            'Macro F1 (%)': round(ov['f1_macro'] * 100, 2),\n",
            "            'Stress F1 (%)': round(ov['f1_stress'] * 100, 2),\n",
            "            'Stress Precision (%)': round(ov.get('precision_stress', 0) * 100, 2),\n",
            "            'Stress Recall (%)': round(ov.get('recall_stress', 0) * 100, 2)\n",
            "        })\n",
            "\n",
            "df_models = pd.DataFrame(summary_rows)\n",
            "display(df_models)\n",
            "\n",
            "# Vẽ biểu đồ so sánh F1 Score giữa các mô hình\n",
            "plt.figure(figsize=(9, 4.5))\n",
            "bars = plt.barh(df_models['Mô hình'], df_models['Stress F1 (%)'], color=['#95A5A6', '#E67E22', '#BDC3C7', '#3498DB', '#2980B9', '#27AE60'], height=0.6)\n",
            "plt.xlabel('Stress F1 Score (%)', fontsize=11)\n",
            "plt.title('Hiệu năng nhận diện Stress của các mô hình (LOSO 15-fold)', fontsize=12, pad=12)\n",
            "for bar in bars:\n",
            "    w = bar.get_width()\n",
            "    plt.text(w + 1, bar.get_y() + bar.get_height()/2.0, f'{w:.1f}%', va='center', fontweight='bold', fontsize=10)\n",
            "plt.xlim(0, 100)\n",
            "plt.grid(axis='x', linestyle='--', alpha=0.4)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]),
        create_cell("markdown", [
            "## 2. Phân tích Tác động của Kênh Nhịp tim (Ablation Study)\n",
            "\n",
            "- Đo lường mức cải thiện khi lần lượt bổ sung các nhóm cảm biến vào mô hình Random Forest.\n",
            "- Bổ sung HR giúp **Stress F1 tăng từ 62,97% lên 73,89%** (+10,92%)."
        ]),
        create_cell("code", [
            "ablation_names = ['Chỉ ACC', 'Chỉ EDA', 'EDA + ACC', 'EDA + ACC + HR (Full)']\n",
            "f1_scores = [\n",
            "    rep['models']['RandomForest_ACC_only']['overall']['f1_stress'] * 100,\n",
            "    rep['models']['RandomForest_EDA_only']['overall']['f1_stress'] * 100,\n",
            "    rep['models']['RandomForest_EDA_and_ACC']['overall']['f1_stress'] * 100,\n",
            "    rep['models']['RandomForest_Full_Multimodal']['overall']['f1_stress'] * 100\n",
            "]\n",
            "\n",
            "plt.figure(figsize=(7.5, 4))\n",
            "plt.plot(ablation_names, f1_scores, marker='o', lw=2.5, color='#2980B9', markersize=8)\n",
            "for x, y in zip(ablation_names, f1_scores):\n",
            "    plt.annotate(f'{y:.2f}%', (x, y), textcoords='offset points', xytext=(0, 10), ha='center', fontweight='bold')\n",
            "plt.ylabel('Stress F1 Score (%)', fontsize=11)\n",
            "plt.ylim(20, 90)\n",
            "plt.title('Đóng góp của từng cảm biến vào hiệu năng nhận diện Stress', fontsize=12, pad=12)\n",
            "plt.grid(True, linestyle='--', alpha=0.4)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]),
        create_cell("markdown", [
            "## 3. Ma trận Nhầm lẫn (Confusion Matrix)\n",
            "\n",
            "- Trực quan hóa số lượng cửa sổ phân loại đúng / sai giữa Bình thường (0) và Stress (1).\n",
            "- So sánh giữa mô hình Random Forest và Logistic Regression."
        ]),
        create_cell("code", [
            "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))\n",
            "\n",
            "cm_rf = np.array(rep['models']['RandomForest_Full_Multimodal']['overall']['confusion_matrix'])\n",
            "cm_lr = np.array(rep['models']['LogisticRegression_Full_Multimodal']['overall']['confusion_matrix'])\n",
            "\n",
            "for ax, cm, title in zip([ax1, ax2], [cm_rf, cm_lr], ['Random Forest (All)', 'Logistic Regression (All)']):\n",
            "    im = ax.imshow(cm, cmap='Blues', interpolation='nearest')\n",
            "    ax.set_title(title, fontsize=11, pad=10)\n",
            "    ax.set_xticks([0, 1])\n",
            "    ax.set_yticks([0, 1])\n",
            "    ax.set_xticklabels(['Bình thường', 'Stress'])\n",
            "    ax.set_yticklabels(['Bình thường', 'Stress'])\n",
            "    ax.set_xlabel('Dự đoán của mô hình')\n",
            "    ax.set_ylabel('Nhãn thực tế')\n",
            "    \n",
            "    for i in range(2):\n",
            "        for j in range(2):\n",
            "            val = cm[i, j]\n",
            "            color = 'white' if val > cm.max()/2 else 'black'\n",
            "            ax.text(j, i, f'{val:,}', ha='center', va='center', color=color, fontweight='bold', fontsize=12)\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ])
    ]
    return nb

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    import sys
    all_generators = [
        ("01-wesad-data-preparation.ipynb", build_nb01),
        ("02-wesad-hr-ecg-review.ipynb", build_nb02),
        ("03-wesad-ppg-benchmark.ipynb", build_nb03),
        ("04-wesad-feature-extraction.ipynb", build_nb04),
        ("05-wesad-model-training.ipynb", build_nb05)
    ]
    
    if len(sys.argv) <= 1:
        print("[-] KHÓA AN TOÀN: Để bảo vệ toàn bộ các chỉnh sửa thủ công của người dùng,")
        print("    script này KHÔNG tự động ghi đè notebook nào khi chạy không có tham số.")
        print("    Nếu thực sự muốn ghi đè notebook nào, hãy truyền đích danh: python scripts/build_notebooks.py <01..05>")
        return
    
    target = sys.argv[1]
    generators = [g for g in all_generators if target in g[0]]
    if not generators:
        print(f"[-] Không tìm thấy notebook khớp với '{target}'.")
        return
    
    for filename, builder in generators:
        filepath = NOTEBOOKS_DIR / filename
        print(f"[*] Building {filename}...")
        nb = builder()
        
        print(f"[*] Executing {filename} via nbclient (kernel python3)...")
        client = NotebookClient(nb, timeout=300, kernel_name="python3")
        client.execute()
        
        print(f"[+] Writing executed notebook to {filepath}...")
        nbformat.write(nb, str(filepath))
        print(f"[✓] {filename} completed with pre-computed outputs!\n")

if __name__ == "__main__":
    main()
