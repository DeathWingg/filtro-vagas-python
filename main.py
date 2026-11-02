#!/usr/bin/env python3
"""
Filtro e adaptador de currículos - v2
Filtros: localização (São Luís/MA) e tipo de contrato (rejeita PJ).
"""
import csv
import json
import re
import sys
from pathlib import Path

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ---------------------- IO ----------------------
def carregar_json(path, nome_amigavel):
    if not Path(path).exists():
        sys.exit(f"[ERRO] Arquivo '{path}' não encontrado ({nome_amigavel}).")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def carregar_vagas(path):
    if not Path(path).exists():
        sys.exit(f"[ERRO] Arquivo '{path}' não encontrado.")
    vagas = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for campo in ("id", "titulo", "empresa", "descricao"):
                if not row.get(campo):
                    print(f"[AVISO] Vaga ignorada (campo '{campo}' vazio): {row}")
                    break
            else:
                vagas.append(row)
    return vagas

# ---------------------- Filtros de exclusão ----------------------
def normalizar(txt):
    return (txt or "").lower()

def eh_pj(texto):
    """Retorna True se a vaga for EXCLUSIVAMENTE PJ."""
    t = normalizar(texto)
    if re.search(r"pj\s*ou\s*clt|clt\s*ou\s*pj|pj/clt|clt/pj", t):
        return False
    padroes = [
        r"\bpj\b", r"pessoa jur[ií]dica", r"\bfreelance\b", r"\bmei\b",
        r"cooperad", r"presta[cç][aã]o de servi[cç]os", r"contrato de presta",
    ]
    return any(re.search(p, t) for p in padroes)

def eh_local_aceito(texto, locais):
    t = normalizar(texto)
    for l in locais:
        if normalizar(l) in t:
            return True
    if re.search(r"[/,-]\s*ma\b", t):
        return True
    return False

def eh_remoto(texto):
    return bool(re.search(r"\bremoto\b|\bhome\s*office\b|\b100%\s*remoto\b", normalizar(texto)))

# ---------------------- Matching ----------------------
def skills_presentes(texto_vaga, skills):
    texto = normalizar(texto_vaga)
    return [s for s in skills if normalizar(s) in texto]

def montar_texto_curriculo(curriculo):
    partes = [curriculo.get("resumo", "")]
    partes.extend(curriculo.get("skills", []))
    partes.extend(curriculo.get("cursos", []))
    for exp in curriculo.get("experiencias", []):
        partes.append(exp.get("cargo", ""))
        partes.extend(exp.get("bullets", []))
    for e in curriculo.get("extras", []):
        partes.append(e.get("titulo", ""))
        partes.append(e.get("descricao", ""))
    return " ".join(partes)

def avaliar_vaga(vaga, curriculo, config):
    texto_vaga = f"{vaga.get('titulo','')} {vaga.get('descricao','')}"
    motivo = None

    # Filtro: PJ
    if config.get("rejeitar_pj") and eh_pj(texto_vaga):
        motivo = "vaga exclusivamente PJ"

    # Filtro: Remoto
    if not motivo and config.get("rejeitar_remoto") and eh_remoto(texto_vaga):
        motivo = "vaga remota (filtro ativo)"

    # Filtro: Localização
    locais = config.get("localizacoes_aceitas") or []
    if not motivo and locais and not eh_local_aceito(f"{vaga.get('local','')} {texto_vaga}", locais):
        motivo = f"localização fora do aceito ({vaga.get('local','?')})"

    # Filtro: Skills obrigatórias
    obrig = config.get("skills_obrigatorias") or []
    if not motivo and obrig:
        exigidas = [s for s in obrig if normalizar(s) in normalizar(texto_vaga)]
        skills_cand = {normalizar(s) for s in curriculo.get("skills", [])}
        faltando = [s for s in exigidas if normalizar(s) not in skills_cand]
        if faltando:
            motivo = f"falta skill obrigatória: {', '.join(faltando)}"

    # Score por keywords
    matched = skills_presentes(texto_vaga, curriculo.get("skills", []))
    total = max(len(curriculo.get("skills", [])), 1)
    score_kw = (len(matched) / total) * 100

    # Score TF-IDF
    score_tfidf = 0.0
    if HAS_SKLEARN and config.get("usar_tfidf", True):
        try:
            vect = TfidfVectorizer(max_features=5000)
            mat = vect.fit_transform([montar_texto_curriculo(curriculo), texto_vaga])
            score_tfidf = float(cosine_similarity(mat[0:1], mat[1:2])[0][0]) * 100
        except ValueError:
            score_tfidf = 0.0

    # Score final
    if HAS_SKLEARN and config.get("usar_tfidf", True):
        tfidf_calibrado = min(score_tfidf * 2.5, 100)
        p_kw = config.get("peso_keywords", 0.7)
        p_tf = config.get("peso_tfidf", 0.3)
        score_final = score_kw * p_kw + tfidf_calibrado * p_tf
    else:
        score_final = score_kw

    return {
        "score_kw": round(score_kw, 1),
        "score_tfidf": round(score_tfidf, 1),
        "score_final": round(score_final, 1),
        "matched": matched,
        "motivo": motivo,
    }

# ---------------------- Adaptação do currículo ----------------------
def reordenar_bullets(experiencias, matched_skills):
    matched_lower = [s.lower() for s in matched_skills]
    resultado = []
    for exp in experiencias:
        def score(bullet):
            b = bullet.lower()
            return sum(1 for s in matched_lower if s in b)
        ordenados = sorted(exp.get("bullets", []), key=score, reverse=True)
        resultado.append((exp, ordenados))
    return resultado

def sanitizar(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)[:80]

def gerar_markdown(curriculo, vaga, matched, bullets_ord, out_path):
    L = []
    L.append(f"# {curriculo['nome']}\n")
    contato = " | ".join(filter(None, [curriculo.get("email"), curriculo.get("telefone"), curriculo.get("linkedin"), curriculo.get("localizacao")]))
    L.append(f"{contato}\n")
    
    if matched:
        L.append("## Destaques para esta vaga\n")
        L.append(", ".join(matched) + "\n")
        
    if curriculo.get("resumo"):
        L.append("## Resumo\n" + curriculo["resumo"] + "\n")
        
    L.append("## Experiência Profissional\n")
    if curriculo.get("experiencias"):
        for exp, bullets in bullets_ord:
            L.append(f"**{exp['cargo']}** — {exp['empresa']} ({exp['periodo']})\n")
            for b in bullets:
                L.append(f"- {b}")
            L.append("")
    else:
        L.append("*Nenhuma experiência formal cadastrada ainda.*\n")
        
    if curriculo.get("extras"):
        L.append("## Experiência Acadêmica e Extracurricular\n")
        for e in curriculo["extras"]:
            L.append(f"**{e['titulo']}** — {e['descricao']}\n")
            
    L.append("## Competências\n")
    todas = matched + [s for s in curriculo.get("skills", []) if s not in matched]
    L.append(", ".join(todas) + "\n")
    
    L.append("## Formação\n")
    for f in curriculo.get("formacao", []):
        L.append(f"- {f.get('curso','')} — {f.get('instituicao','')} ({f.get('periodo','')})")
        
    Path(out_path).write_text("\n".join(L), encoding="utf-8")

def gerar_docx(curriculo, vaga, matched, bullets_ord, out_path):
    doc = Document()
    doc.add_heading(curriculo["nome"], level=0)
    contato = " | ".join(filter(None, [curriculo.get("email"), curriculo.get("telefone"), curriculo.get("linkedin"), curriculo.get("localizacao")]))
    doc.add_paragraph(contato)

    if matched:
        doc.add_heading("Destaques para esta vaga", level=1)
        doc.add_paragraph(", ".join(matched))

    if curriculo.get("resumo"):
        doc.add_heading("Resumo", level=1)
        doc.add_paragraph(curriculo["resumo"])

    doc.add_heading("Experiência Profissional", level=1)
    if curriculo.get("experiencias"):
        for exp, bullets in bullets_ord:
            p = doc.add_paragraph()
            p.add_run(exp["cargo"]).bold = True
            doc.add_paragraph(f"{exp['empresa']} — {exp['periodo']}")
            for b in bullets:
                doc.add_paragraph(b, style="List Bullet")
    else:
        doc.add_paragraph("Nenhuma experiência formal cadastrada ainda.")

    if curriculo.get("extras"):
        doc.add_heading("Experiência Acadêmica e Extracurricular", level=1)
        for e in curriculo["extras"]:
            p = doc.add_paragraph()
            p.add_run(e["titulo"]).bold = True
            doc.add_paragraph(e["descricao"])

    doc.add_heading("Competências", level=1)
    todas = matched + [s for s in curriculo.get("skills", []) if s not in matched]
    doc.add_paragraph(", ".join(todas))

    doc.add_heading("Formação", level=1)
    for f in curriculo.get("formacao", []):
        doc.add_paragraph(f"{f.get('curso','')} — {f.get('instituicao','')} ({f.get('periodo','')})")

    doc.save(out_path)

# ---------------------- Main ----------------------
def main():
    print("=" * 60)
    print(" FILTRO E ADAPTADOR DE CURRÍCULOS - v2")
    print("=" * 60)

    config = carregar_json("config.json", "configuração")
    curriculo = carregar_json("curriculo_base.json", "currículo base")
    vagas = carregar_vagas("vagas.csv")

    print(f"Currículo: {curriculo['nome']}")
    print(f"Vagas para avaliar: {len(vagas)}")
    print(f"Limiar de aprovação: {config.get('limiar', 30)}%")
    print(f"Filtro PJ ativo: {config.get('rejeitar_pj')}")
    print(f"Localizações aceitas: {', '.join(config.get('localizacoes_aceitas', []))}\n")

    Path("output/curriculos").mkdir(parents=True, exist_ok=True)

    relatorio = []
    aprovadas = 0

    for vaga in vagas:
        r = avaliar_vaga(vaga, curriculo, config)
        limiar = config.get("limiar", 30)
        aprovada = r["score_final"] >= limiar and r["motivo"] is None
        status = "APROVADA" if aprovada else "REJEITADA"

        print(f"[{status}] {vaga['titulo']} @ {vaga['empresa']}")
        print(f"           score: {r['score_final']:.1f}%")
        if not aprovada:
            print(f"           motivo: {r['motivo'] or 'score abaixo do limiar'}")

        if aprovada:
            aprovadas += 1
            bullets_ord = reordenar_bullets(curriculo.get("experiencias", []), r["matched"])
            nome_base = sanitizar(f"{vaga['id']}_{vaga['empresa']}_{vaga['titulo']}")
            if HAS_DOCX:
                gerar_docx(curriculo, vaga, r["matched"], bullets_ord, f"output/curriculos/{nome_base}.docx")
            else:
                gerar_markdown(curriculo, vaga, r["matched"], bullets_ord, f"output/curriculos/{nome_base}.md")

        relatorio.append({
            "id": vaga["id"],
            "titulo": vaga["titulo"],
            "empresa": vaga["empresa"],
            "local": vaga.get("local", ""),
            "score_kw": r["score_kw"],
            "score_tfidf": r["score_tfidf"],
            "score_final": r["score_final"],
            "status": status,
            "motivo": r["motivo"] or "",
            "skills_match": ", ".join(r["matched"]),
            "link": vaga.get("link", ""),
        })

    if relatorio:
        with open("output/relatorio.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=relatorio[0].keys())
            w.writeheader()
            w.writerows(relatorio)

    print("\n" + "=" * 60)
    print(f"Resumo: {aprovadas} aprovadas de {len(vagas)} vagas.")
    print("Relatório: output/relatorio.csv")
    print("Currículos: output/curriculos/")
    print("=" * 60)

if __name__ == "__main__":
    main()
