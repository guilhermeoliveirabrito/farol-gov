"""Converte data/sem_site.csv no json enxuto que o mapa da pagina usa."""
import csv
import json
import sys


def converter(entrada, saida):
    pontos = []
    with open(entrada, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            try:
                lat, lon = round(float(linha["lat"]), 3), round(float(linha["lon"]), 3)
            except (KeyError, ValueError):
                continue
            pontos.append([linha["ibge"], linha["municipio"], linha["uf"], lat, lon])
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(pontos, f, ensure_ascii=False, separators=(",", ":"))
    return len(pontos)


if __name__ == "__main__":
    print(f"{converter(sys.argv[1], sys.argv[2])} municipios sem site")
