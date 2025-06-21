from flask import Flask, request, jsonify, send_file
import os
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
import json

app = Flask(__name__)

# Configurações
ASSETS_FILE = "assets.txt"  # Arquivo com a lista de itens
CDN_URL = "https://freefiremobile-a.akamaihd.net/common/Local/PK/FF_UI_Icon"

def load_assets():
    assets = {}
    try:
        with open(ASSETS_FILE, 'r', encoding='utf-8') as f:
            items = json.load(f)
            for item in items:
                if 'itemID' in item and 'icon' in item:
                    # Salva por ID decimal
                    assets[str(item['itemID'])] = item
                    # Salva por ID hexadecimal formatado
                    hex_id = f"{int(item['itemID']):08X}"
                    hex_formatted = ' '.join([hex_id[i:i+2] for i in range(6, -1, -2)])
                    assets[hex_formatted] = item
    except Exception as e:
        print(f"Erro ao carregar assets: {str(e)}")
    return assets

ASSETS_DB = load_assets()

def apply_rarity_effects(img, rarity):
    """Aplica um fundo conforme a raridade do item"""
    rarity_backgrounds = {
        "BLUE": "backgrounds/blue.png",
        "PURPLE": "backgrounds/purple.png",
        "ORANGE": "backgrounds/orange.png",
        "RED": "backgrounds/red.png"
    }

    rarity = rarity.upper()
    if rarity not in rarity_backgrounds:
        return img  # Se for WHITE ou outra não tratada, devolve a imagem original

    try:
        background_path = rarity_backgrounds[rarity]
        if not os.path.exists(background_path):
            print(f"Fundo de raridade '{rarity}' não encontrado em: {background_path}")
            return img

        bg = Image.open(background_path).convert("RGBA")
        bg = bg.resize(img.size)  # Garante que o fundo tenha o mesmo tamanho da imagem
        result = Image.alpha_composite(bg, img)  # Combina o fundo com o ícone
        return result

    except Exception as e:
        print(f"Erro ao aplicar fundo de raridade: {str(e)}")
        return img

@app.route('/library/icons', methods=['GET'])
def get_icon():
    icon_id = request.args.get('id')
    if not icon_id:
        return jsonify({"error": "ID parameter is required"}), 400

    # Busca o item no banco de dados
    item_data = ASSETS_DB.get(icon_id)

    # Se não encontrou, tenta a versão hexadecimal
    if not item_data and icon_id.isdigit():
        hex_id = f"{int(icon_id):08X}"
        hex_formatted = ' '.join([hex_id[i:i+2] for i in range(6, -1, -2)])
        item_data = ASSETS_DB.get(hex_formatted)

    if not item_data or 'icon' not in item_data:
        return jsonify({
            "error": "Icon not found",
            "tried_id": icon_id,
            "available_ids": list(ASSETS_DB.keys())[:10]
        }), 404

    try:
        icon_name = item_data['icon']
        rarity = item_data.get('Rare', 'WHITE').upper()

        response = requests.get(f"{CDN_URL}/{icon_name}.png", timeout=10)
        if response.status_code != 200:
            return jsonify({
                "error": "CDN resource not found",
                "cdn_url": f"{CDN_URL}/{icon_name}.png"
            }), 404

        img = Image.open(BytesIO(response.content)).convert("RGBA")

        # Aplica o fundo de raridade
        img = apply_rarity_effects(img, rarity)

        # Adiciona a marca d'água
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        text = "Tanhung11231"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (img.width - (bbox[2] - bbox[0])) // 2
        y = (img.height - (bbox[3] - bbox[1])) // 2

        # Sombra
        draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, 128))
        # Texto principal
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        return send_file(img_bytes, mimetype='image/png')

    except Exception as e:
        return jsonify({
            "error": "Image processing failed",
            "details": str(e)
        }), 500

@app.route('/library/item_info', methods=['GET'])
def get_item_info():
    """Rota para obter informações completas do item"""
    item_id = request.args.get('id')
    if not item_id:
        return jsonify({"error": "ID parameter is required"}), 400

    item_data = ASSETS_DB.get(item_id)
    if not item_data and item_id.isdigit():
        hex_id = f"{int(item_id):08X}"
        hex_formatted = ' '.join([hex_id[i:i+2] for i in range(6, -1, -2)])
        item_data = ASSETS_DB.get(hex_formatted)

    if not item_data:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(item_data)

if __name__ == "__main__":
    if not os.path.exists(ASSETS_FILE):
        print(f"AVISO: Arquivo {ASSETS_FILE} não encontrado!")
    app.run(host='0.0.0.0', port=5019)