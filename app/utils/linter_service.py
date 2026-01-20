# /app/utils/linter_service.py

from yamllint import linter
from yamllint.config import YamlLintConfig
from ruamel.yaml import YAML
import tempfile
import os
import io
import logging

# Siapkan logger untuk file ini jika diperlukan
logger = logging.getLogger(__name__)

def run_yaml_linting(content: str) -> dict:
    """
    Menjalankan validasi dan linting pada konten YAML dalam dua tahap.
    
    Returns:
        dict: Berisi 'status' dan data pendukungnya.
    """
    if not content:
        return {"status": "INVALID_SYNTAX", "error_message": "Konten tidak boleh kosong."}

    # Tahap 1: Validasi Sintaksis dengan ruamel.yaml
    yaml_parser = YAML()
    try:
        yaml_parser.load(content)
    except Exception as e:
        logger.warning(f"Invalid YAML syntax: {e}")
        return {"status": "INVALID_SYNTAX", "error_message": f"Kesalahan sintaksis YAML: {str(e)}"}

    # Tahap 2: Validasi Kualitas (Linting) dengan yamllint
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml', encoding='utf-8') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        conf = YamlLintConfig('extends: default')
        with open(tmp_path, 'r', encoding='utf-8') as tmp_file:
            problems = list(linter.run(tmp_file, conf, tmp_path))
        
        results = [{'line': p.line, 'col': p.column, 'level': p.level, 'message': p.desc} for p in problems]

        if not results:
            return {"status": "PERFECT", "problems": []}
        else:
            return {"status": "VALID_WITH_ISSUES", "problems": results}

    except Exception as e:
        logger.exception("Error during yamllint process")
        raise e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# [FUNGSI YANG PERLU DITAMBAHKAN]
def auto_fix_yaml(content: str) -> str:
    """
    Mencoba memperbaiki masalah umum pada konten YAML.
    - Menambahkan '---' jika tidak ada (explicit start).
    - Memperbaiki indentasi (standard 2 spaces) dan format dasar.
    - Mendukung multi-document YAML.
    
    Args:
        content (str): String berisi teks YAML yang akan diperbaiki.

    Returns:
        str: Konten YAML yang sudah diformat dan diperbaiki.
    """
    if not content or not content.strip():
        return content

    yaml = YAML()
    # Konfigurasi indentasi standar:
    # mapping=2: indentasi anak key 2 spasi
    # sequence=4: indentasi list (dash) 4 spasi dari parent (2 spasi extra)
    # offset=2: jarak antara dash dan kontennya
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    yaml.explicit_start = True  # Paksa '---' di awal dokumen
    yaml.width = 4096           # Hindari wrapping line yang tidak perlu

    try:
        # Gunakan load_all untuk mendukung multi-document (misal K8s manifests)
        data = list(yaml.load_all(content))
        
        # Jika hasil load kosong (misal hanya komentar), kembalikan aslinya
        if not data:
            return content

        string_stream = io.StringIO()
        yaml.dump_all(data, string_stream)
        fixed_content = string_stream.getvalue()
        
        # ruamel.yaml kadang tidak menambahkan newline di akhir file
        if not fixed_content.endswith('\n'):
            fixed_content += '\n'
            
        return fixed_content

    except Exception as e:
        # Jika gagal memparsing (syntax fatal), kembalikan konten asli
        # agar user bisa memperbaiki manual berdasarkan error linter.
        logger.warning(f"Auto-fix failed (syntax error?): {e}")
        return content
