import streamlit as st
import sqlite3
import json
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from typing import Literal
from fpdf import FPDF

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# ==========================================
def inicializar_banco():
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS avaliacao_risco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT NOT NULL,
            score_total REAL,
            faixa_risco TEXT,
            memoria_calculo TEXT NOT NULL,
            data_avaliacao TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saude_integrada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT NOT NULL,
            score_pclr INTEGER,
            laudo_pclr TEXT,
            risco_suicidio TEXT,
            risco_psicose TEXT,
            alerta_infeccao TEXT,
            data_avaliacao TEXT
        )
    ''')
    conexao.commit()
    conexao.close()

inicializar_banco()

def salvar_avaliacao(nome, matricula, score_total, faixa_risco, memoria_calculo):
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO avaliacao_risco (nome, matricula, score_total, faixa_risco, memoria_calculo, data_avaliacao)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nome, matricula, score_total, faixa_risco, json.dumps(memoria_calculo), data_hoje))
    conexao.commit()
    conexao.close()
    
def salvar_saude(nome, matricula, score_pclr, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao):
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO saude_integrada (nome, matricula, score_pclr, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao, data_avaliacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nome, matricula, score_pclr, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao, data_hoje))
    conexao.commit()
    conexao.close()

def buscar_dados_custodiado(matricula):
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    cursor.execute("SELECT nome FROM avaliacao_risco WHERE matricula = ? ORDER BY id DESC LIMIT 1", (matricula,))
    risco = cursor.fetchone()
    cursor.execute("SELECT nome, laudo_pclr, risco_suicidio, alerta_infeccao FROM saude_integrada WHERE matricula = ? ORDER BY id DESC LIMIT 1", (matricula,))
    saude = cursor.fetchone()
    conexao.close()
    
    nome_encontrado = risco[0] if risco else (saude[0] if saude else "")
    laudo_psi = saude[1] if saude else None
    risco_sui = saude[2] if saude else None
    infeccao = saude[3] if saude else None
    return nome_encontrado, laudo_psi, risco_sui, infeccao

# ==========================================
# 2. MOTOR ATUARIAL E GERAÇÃO DE PDFs
# ==========================================
@dataclass
class FatorRisco:
    codigo: str
    descricao: str
    categoria: Literal["estatico", "dinamico", "clinico"]
    peso: float
    fonte_legal: str
    valor_observado: float 
    justificativa: str 

    @property
    def pontuacao(self) -> float:
        return round(self.peso * self.valor_observado, 3)

def calcular_score(fatores: list[FatorRisco]) -> dict:
    total = sum(f.pontuacao for f in fatores)
    if total >= 80: faixa = "Alto Risco (Isolamento/Monitoramento Máximo)"
    elif total >= 40: faixa = "Médio Risco"
    else: faixa = "Baixo Risco (Elegível a Progressão)"
    return {"score_total": round(total, 3), "faixa_risco": faixa, "memoria_calculo": [{**f.__dict__, 'pontuacao': f.pontuacao} for f in fatores]}

# PDF 1: Parecer Jurídico Simples (Intake)
def gerar_pdf(nome, matricula, score_total, faixa_risco, memoria_calculo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 10, "PARECER TÉCNICO CONSULTIVO - ORION-PEN", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 10, "Sistema Inteligente de Avaliação de Risco e Otimização Carcerária", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 10, f"Custodiado: {nome}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Matrícula / Prontuário: {matricula}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Data da Avaliação: {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("helvetica", style="B", size=14)
    pdf.cell(0, 10, f"RESULTADO FINAL: {faixa_risco} (Score: {score_total})", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 10, "MEMÓRIA DE CÁLCULO E JUSTIFICATIVAS:", new_x="LMARGIN", new_y="NEXT")
    
    for item in memoria_calculo:
        pdf.set_font("helvetica", style="B", size=10)
        pdf.multi_cell(0, 8, f"{item['codigo']} | {item['descricao']} | Pontuação: {item['pontuacao']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=10)
        pdf.multi_cell(0, 6, f"Base Legal: {item['fonte_legal']}", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 6, f"Justificativa: {item['justificativa']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        
    pdf.ln(5)
    pdf.set_font("helvetica", style="I", size=9)
    pdf.multi_cell(0, 5, "TERMO DE CONFORMIDADE: Parecer técnico consultivo (white-box). A decisão final é soberana e compete exclusivamente à autoridade judicial ou administrativa competente.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

# PDF 2: Dossiê Unificado (BI) COM CITAÇÕES CIENTÍFICAS E JUSTIFICATIVAS COMPLETAS
def gerar_dossie_completo_pdf(matricula):
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    cursor.execute("SELECT nome, score_total, faixa_risco, memoria_calculo, data_avaliacao FROM avaliacao_risco WHERE matricula = ? ORDER BY id DESC LIMIT 1", (matricula,))
    risco = cursor.fetchone()
    cursor.execute("SELECT laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao, data_avaliacao FROM saude_integrada WHERE matricula = ? ORDER BY id DESC LIMIT 1", (matricula,))
    saude = cursor.fetchone()
    conexao.close()

    if not risco and not saude:
        return None

    nome_custodiado = risco[0] if risco else buscar_dados_custodiado(matricula)[0]

    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 10, "DOSSIÊ UNIFICADO DE GOVERNANÇA CARCERÁRIA", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 10, "ORION-Pen - Triagem Jurídica e Clínica", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)

    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, f"Custodiado: {nome_custodiado}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Matrícula / Prontuário: {matricula}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 1. Seção Saúde
    pdf.set_font("helvetica", style="B", size=14)
    pdf.set_text_color(150, 0, 0)
    pdf.cell(0, 10, "1. AVALIAÇÃO GLOBAL DE SAÚDE E PSIQUIATRIA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    
    if saude:
        pdf.set_font("helvetica", size=11)
        pdf.cell(0, 8, f"Data da Avaliação Clínica: {saude[4]}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", style="B", size=11)
        pdf.cell(0, 8, f"Risco de Violência (PCL-R): {saude[0]}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Risco de Suicídio (C-SSRS): {saude[1]}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Transtornos Psicóticos: {saude[2]}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Alerta Infectocontagioso: {saude[3]}", new_x="LMARGIN", new_y="NEXT")
        
        # --- BLOCO DE FONTES CIENTÍFICAS ---
        pdf.ln(3)
        pdf.set_font("helvetica", style="B", size=9)
        pdf.set_text_color(100, 100, 100) # Cor cinza escuro
        pdf.cell(0, 5, "FONTES E PROTOCOLOS CIENTÍFICOS APLICADOS:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=8)
        pdf.multi_cell(0, 4, "- PCL-R (Hare Psychopathy Checklist-Revised): Padrão-ouro global para predição de reincidência violenta e psicopatia criminal.", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, "- C-SSRS (Columbia-Suicide Severity Rating Scale): Protocolo oficial de triagem endossado pela OMS e pelo FDA.", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, "- Triagem BPRS-A (Brief Psychiatric Rating Scale): Matriz avaliativa para quadros psicóticos e conversão penal.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0) # Retorna para preto
    else:
        pdf.set_font("helvetica", style="I", size=11)
        pdf.cell(0, 8, "Nenhum laudo clínico ou psiquiátrico registrado para esta matrícula.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 2. Seção Jurídica
    pdf.set_font("helvetica", style="B", size=14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "2. PARECER ATUARIAL E JURÍDICO (WHITE-BOX)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    
    if risco:
        pdf.set_font("helvetica", size=11)
        pdf.cell(0, 8, f"Data da Avaliação Jurídica: {risco[4]}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", style="B", size=12)
        pdf.cell(0, 8, f"Classificação Final de Risco: {risco[2]} (Score: {risco[1]})", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("helvetica", style="B", size=11)
        pdf.cell(0, 8, "Memória de Cálculo Resumida:", new_x="LMARGIN", new_y="NEXT")
        
        memoria = json.loads(risco[3])
        for item in memoria:
            pdf.set_font("helvetica", style="B", size=10)
            pdf.multi_cell(0, 6, f"{item['codigo']} | {item['descricao']} | Pontuação: {item['pontuacao']}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", size=10)
            # CORREÇÃO APLICADA AQUI: Imprimindo a justificativa real no Dossiê
            pdf.multi_cell(0, 6, f"Base Legal: {item['fonte_legal']}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 6, f"Justificativa: {item['justificativa']}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
    else:
        pdf.set_font("helvetica", style="I", size=11)
        pdf.cell(0, 8, "Nenhuma avaliação atuarial registrada para esta matrícula.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("helvetica", style="I", size=9)
    pdf.multi_cell(0, 5, "TERMO DE CONFORMIDADE: Dossiê gerado eletronicamente integrando as bases clínicas e atuariais do sistema. O ORION-Pen emite parecer consultivo, respeitando a soberania da decisão judicial.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

# ==========================================
# 3. CAMADA DE APRESENTAÇÃO E NAVEGAÇÃO
# ==========================================
st.set_page_config(page_title="ORION-Pen", layout="wide")
st.sidebar.title("⚖️ ORION-Pen")
menu = st.sidebar.radio("Navegação do Sistema:", ["📝 Nova Avaliação (Intake)", "🩺 Saúde Integrada (Mental e Clínica)", "📊 Painel da Gestão (BI)"])
st.sidebar.markdown("---")
st.sidebar.info("Proteção Legal: Arquitetura White-Box Ativa")

# ==========================================
# MÓDULO 1: INTAKE (Formulário Jurídico Completo Restaurado)
# ==========================================
if menu == "📝 Nova Avaliação (Intake)":
    st.title("Formulário de Entrevista Técnica (Intake)")
    st.info("Para garantir a segurança jurídica, todos os campos de justificativa exigem fundamentação detalhada (mínimo de 50 caracteres).")
    
    matricula = st.text_input("🔍 Matrícula / Prontuário (Digite e pressione Enter):")
    nome_sugerido, alerta_psi, alerta_sui, alerta_inf = "", None, None, None
    
    if matricula:
        nome_busca, laudo_psi, risco_sui, infeccao = buscar_dados_custodiado(matricula)
        if nome_busca:
            nome_sugerido = nome_busca
            st.success("✅ Prontuário localizado na base de dados!")
        if risco_sui == "ALTO RISCO (Alerta Vermelho)":
            st.error("🚨 **ALERTA GRAVE:** Detento com risco iminente de suicídio. **NÃO COLOCAR EM CELA ISOLADA (SEGURO).**")
        if infeccao == "SIM (Isolamento Necessário)":
            st.error("☣️ **ALERTA MÉDICO:** Detento apresenta sintomas infectocontagiosos. **NECESSÁRIO ISOLAMENTO RESPIRATÓRIO.**")
        if laudo_psi and "ALTO RISCO" in laudo_psi:
            st.warning(f"⚠️ **Atenção:** Um laudo clínico foi encontrado para este detento: **{laudo_psi}**.")

    nome = st.text_input("Nome do Custodiado:", value=nome_sugerido)
    
    st.markdown("---")
    st.write("### I. Fatores Clínicos e Psicológicos")
    
    opcoes_pclr = {
        "Não Avaliado / Traços Inexpressivos": 0.0,
        "MÉDIO RISCO (Presença de Traços Antissociais)": 20.0,
        "ALTO RISCO (Alta Compatibilidade com Psicopatia)": 45.0
    }
    val_psicopatia = st.selectbox("Laudo Psicológico Prévio (Escala PCL-R):", list(opcoes_pclr.keys()))
    just_psicopatia = st.text_area("Justificativa (Fator Clínico):", placeholder="Ex: O custodiado foi submetido ao protocolo PCL-R pela equipe de psicologia forense, totalizando score compatível...")
    
    st.markdown("---")
    st.write("### II. Fatores Estáticos (Passado Imutável)")
    col_est1, col_est2 = st.columns(2)
    with col_est1:
        val_iniciacao = st.selectbox("1. Início da trajetória criminal antes dos 18 anos?", ["Não", "Sim"])
        just_iniciacao = st.text_area("Justificativa (Fator 1):", placeholder="Ex: Conforme análise do histórico, o primeiro registro infracional ocorreu aos 19 anos...")
        
        opcoes_crime = {
            "Nenhum antecedente relevante": 0.0,
            "Patrimonial Sem Violência (ex: Furto, Estelionato)": 10.0,
            "Lei de Drogas / Tráfico": 15.0,
            "Patrimonial Com Violência (ex: Roubo)": 25.0,
            "Contra a Vida / Hediondo (ex: Homicídio)": 35.0
        }
        val_natureza = st.selectbox("2. Natureza do Delito Principal:", list(opcoes_crime.keys()))
        just_natureza = st.text_area("Justificativa Obrigatória (Fator 2):", placeholder="Ex: Conforme sentença condenatória às fls. 45, cumpre pena pelo Art. 171...")

    with col_est2:
        val_reincidencia = st.selectbox("3. Possui reincidência com trânsito em julgado?", ["Não", "Sim"])
        just_reincidencia = st.text_area("Justificativa (Fator 3):", placeholder="Ex: A certidão de antecedentes criminais atualizada demonstra ausência de condenações...")
        
        val_fuga = st.selectbox("4. Histórico registrado de evasão ou falta grave (fuga)?", ["Não", "Sim"])
        just_fuga = st.text_area("Justificativa (Fator 4):", placeholder="Ex: O prontuário disciplinar da unidade não registra Processos Administrativos Disciplinares (PADs)...")

    st.markdown("---")
    st.write("### III. Fatores Dinâmicos (Contexto Atual e Reabilitação)")
    col_din1, col_din2 = st.columns(2)
    with col_din1:
        val_faccao = st.selectbox("5. Pertencimento a facção com lastro documental?", ["Não", "Sim"])
        just_faccao = st.text_area("Justificativa e Fonte Documental (Fator 5):", placeholder="Ex: O Relatório de Inteligência Penitenciária nº 12/2026 aponta ausência de vínculos ativos...")

        val_quimica = st.selectbox("6. Avaliação clínica formal indica dependência química?", ["Não", "Sim"])
        just_quimica = st.text_area("Justificativa (Fator 6):", placeholder="Ex: A avaliação psicossocial atesta uso abusivo de entorpecentes, havendo recomendação...")

    with col_din2:
        val_disciplina = st.selectbox("7. Faltas disciplinares graves nos últimos 12 meses?", ["Não", "Sim"])
        just_disciplina = st.text_area("Justificativa (Fator 7):", placeholder="Ex: O Boletim Informativo (BI) da unidade atesta bom comportamento carcerário...")
        
        val_trabalho = st.selectbox("8. Engajado formalmente visando remição?", ["Não", "Sim (Reduz Risco)"])
        just_trabalho = st.text_area("Justificativa (Fator 8):", placeholder="Ex: Declaração do setor de laborterapia comprova trabalho regular na manutenção predial...")

    if st.button("Gerar Parecer Jurídico"):
        campos_justificativa = {
            "Fator Clínico": just_psicopatia, "Fator 1 (Iniciação)": just_iniciacao, "Fator 2 (Natureza)": just_natureza,
            "Fator 3 (Reincidência)": just_reincidencia, "Fator 4 (Fuga)": just_fuga, "Fator 5 (Facção)": just_faccao,
            "Fator 6 (Dep. Química)": just_quimica, "Fator 7 (Disciplina)": just_disciplina, "Fator 8 (Trabalho)": just_trabalho
        }
        erros_tamanho = [nome_campo for nome_campo, texto in campos_justificativa.items() if len(texto.strip()) < 50]
        
        if not nome or not matricula:
            st.error("Erro: Preencha o nome e a matrícula.")
        elif erros_tamanho:
            st.error("⚠️ **Erro Jurídico:** Os seguintes campos não atingiram o detalhamento técnico mínimo (50 caracteres):")
            for erro in erros_tamanho: st.write(f"- {erro}")
        else:
            fatores = [
                FatorRisco("CLI-01", f"Perfil Psicológico: {val_psicopatia}", "clinico", opcoes_pclr[val_psicopatia], "PCL-R", 1.0, just_psicopatia),
                FatorRisco("EST-01", "Idade iniciação precoce", "estatico", 15.0, "Criminologia Aplicada", 1.0 if val_iniciacao == "Sim" else 0.0, just_iniciacao),
                FatorRisco("EST-02", f"Natureza do Delito: {val_natureza}", "estatico", opcoes_crime[val_natureza], "Art. 112, LEP", 1.0, just_natureza),
                FatorRisco("EST-03", "Reincidência formal", "estatico", 20.0, "Art. 63, CP", 1.0 if val_reincidencia == "Sim" else 0.0, just_reincidencia),
                FatorRisco("EST-04", "Antecedentes evasão/fuga", "estatico", 25.0, "Histórico Disciplinar", 1.0 if val_fuga == "Sim" else 0.0, just_fuga),
                FatorRisco("DIN-01", "Vínculo organização criminosa", "dinamico", 35.0, "Lei nº 12.850/2013", 1.0 if val_faccao == "Sim" else 0.0, just_faccao),
                FatorRisco("DIN-02", "Dependência química", "dinamico", 15.0, "Lei nº 11.343/2006", 1.0 if val_quimica == "Sim" else 0.0, just_quimica),
                FatorRisco("DIN-03", "Faltas disciplinares (12m)", "dinamico", 20.0, "Art. 51-52, LEP", 1.0 if val_disciplina == "Sim" else 0.0, just_disciplina),
                FatorRisco("DIN-04", "Engajamento estudo/trabalho", "dinamico", -20.0, "Art. 126, LEP", 1.0 if val_trabalho == "Sim (Reduz Risco)" else 0.0, just_trabalho)
            ]
            resultado = calcular_score(fatores)
            salvar_avaliacao(nome, matricula, resultado['score_total'], resultado['faixa_risco'], resultado['memoria_calculo'])
            st.success("Avaliação processada e salva com sucesso!")
            st.download_button("📥 Baixar Parecer Oficial em PDF", gerar_pdf(nome, matricula, resultado['score_total'], resultado['faixa_risco'], resultado['memoria_calculo']), f"Parecer_ORION_{matricula}.pdf", "application/pdf")

# ==========================================
# MÓDULO 2: SAÚDE INTEGRADA (Calculado por Perguntas)
# ==========================================
elif menu == "🩺 Saúde Integrada (Mental e Clínica)":
    st.title("Triagem de Saúde e Psiquiatria Forense")
    st.write("Módulo de Saúde Global: Baseado na Escala PCL-R, C-SSRS (Suicídio) e Triagem Infectológica.")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        matricula_psi = st.text_input("Matrícula (Busca automática):")
        nome_sugerido_psi = buscar_dados_custodiado(matricula_psi)[0] if matricula_psi else ""
    with col2:
        nome_psi = st.text_input("Nome do Paciente:", value=nome_sugerido_psi)
        
    st.markdown("### 1. Risco de Violência e Psicopatia (Inventário PCL-R)")
    st.info("Instrução Clínica: Pontue cada item para calcular o score automaticamente. 0 = Ausente; 1 = Parcialmente; 2 = Presente.")
    opcoes_pontos = {"0 (Ausente)": 0, "1 (Parcialmente)": 1, "2 (Presente)": 2}
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Fator 1: Interpessoal e Afetivo**")
        i1 = st.radio("1. Charme superficial e eloquência", list(opcoes_pontos.keys()), key="i1")
        i2 = st.radio("2. Sentimento grandioso de valor próprio", list(opcoes_pontos.keys()), key="i2")
        i3 = st.radio("3. Mentira patológica / Manipulação", list(opcoes_pontos.keys()), key="i3")
        i4 = st.radio("4. Ausência de remorso ou culpa", list(opcoes_pontos.keys()), key="i4")
        i5 = st.radio("5. Falta de empatia / Frieza emocional", list(opcoes_pontos.keys()), key="i5")

    with col_b:
        st.markdown("**Fator 2: Estilo de Vida e Antissocial**")
        i6 = st.radio("6. Impulsividade", list(opcoes_pontos.keys()), key="i6")
        i7 = st.radio("7. Irresponsabilidade contínua", list(opcoes_pontos.keys()), key="i7")
        i8 = st.radio("8. Necessidade de estimulação / Tendência ao tédio", list(opcoes_pontos.keys()), key="i8")
        i9 = st.radio("9. Histórico de delinquência juvenil", list(opcoes_pontos.keys()), key="i9")
        i10 = st.radio("10. Revogação de condicional anterior", list(opcoes_pontos.keys()), key="i10")

    st.markdown("---")
    st.markdown("### 2. Triagem de Risco de Suicídio (Protocolo Columbia - C-SSRS)")
    sui_1 = st.selectbox("O detento expressou desejo recente de estar morto ou tirar a própria vida?", ["Não", "Sim"])
    sui_2 = st.selectbox("O detento elaborou algum método, plano ou intenção ativa?", ["Não", "Sim"])
    
    st.markdown("---")
    st.markdown("### 3. Transtornos Psicóticos (Conversão para Medida de Segurança)")
    psi_1 = st.selectbox("Apresenta delírios, alucinações severas ou desorganização aguda do pensamento?", ["Não", "Sim (Incompatível com Sistema Comum)"])
    
    st.markdown("---")
    st.markdown("### 4. Triagem Infectocontagiosa (Tuberculose, Sarna, COVID)")
    inf_1 = st.selectbox("Apresenta tosse persistente (mais de 3 semanas), febre, lesões de pele ativas ou suspeita de vírus?", ["Não", "Sim"])
    
    if st.button("Calcular e Salvar Prontuário Global de Saúde"):
        if not nome_psi or not matricula_psi:
            st.error("Preencha os dados do paciente.")
        else:
            score_parcial = (opcoes_pontos[i1] + opcoes_pontos[i2] + opcoes_pontos[i3] + opcoes_pontos[i4] + opcoes_pontos[i5] + 
                             opcoes_pontos[i6] + opcoes_pontos[i7] + opcoes_pontos[i8] + opcoes_pontos[i9] + opcoes_pontos[i10])
            score_final = score_parcial * 2 
            
            if score_final >= 30:
                laudo_pclr = "ALTO RISCO (Alta Compatibilidade com Psicopatia)"
            elif score_final >= 20:
                laudo_pclr = "MÉDIO RISCO (Presença de Traços Antissociais)"
            else:
                laudo_pclr = "BAIXO RISCO (Traços Psicopáticos Inexpressivos)"
                
            risco_suicidio = "ALTO RISCO (Alerta Vermelho)" if sui_1 == "Sim" or sui_2 == "Sim" else "Baixo/Nenhum Risco"
            risco_psicose = "ALERTA PSICÓTICO (Sugerir HCTP)" if "Sim" in psi_1 else "Sem traços psicóticos"
            alerta_infeccao = "SIM (Isolamento Necessário)" if inf_1 == "Sim" else "Liberado (Apto para Galeria)"

            salvar_saude(nome_psi, matricula_psi, score_final, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao)
            
            st.success("Prontuário Médico e Psicológico processado e salvo!")
            st.markdown(f"**Resultado PCL-R Calculado:** {score_final}/40 - {laudo_pclr}")
            st.warning("Recomendação: O sistema emitirá alertas automáticos caso este detento seja submetido à triagem jurídica.")

# ==========================================
# MÓDULO 3: PAINEL DA GESTÃO E EXPORTAÇÃO DE DOSSIÊ
# ==========================================
elif menu == "📊 Painel da Gestão (BI)":
    st.title("Painel Executivo e Visão 360º (GovTech)")
    
    conexao = sqlite3.connect('orion_pen.db')
    df_risco = pd.read_sql_query("SELECT nome, matricula, score_total, faixa_risco FROM avaliacao_risco", conexao)
    df_saude = pd.read_sql_query("SELECT matricula, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao FROM saude_integrada", conexao)
    conexao.close()
    
    if df_risco.empty and df_saude.empty:
        st.info("Nenhuma avaliação foi registrada no sistema ainda.")
    else:
        if not df_risco.empty: df_risco = df_risco.drop_duplicates(subset=['matricula'], keep='last')
        if not df_saude.empty: df_saude = df_saude.drop_duplicates(subset=['matricula'], keep='last')

        baixo_risco = len(df_risco[df_risco['faixa_risco'].str.contains("Baixo Risco")]) if not df_risco.empty else 0
        risco_suicidio_kpi = len(df_saude[df_saude['risco_suicidio'].str.contains("ALTO RISCO")]) if not df_saude.empty else 0
        infeccao_kpi = len(df_saude[df_saude['alerta_infeccao'].str.contains("SIM")]) if not df_saude.empty else 0
        economia_potencial = baixo_risco * 2637.75 
        
        st.markdown("### 🚨 Painel de Crise e Alertas")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Elegíveis à Progressão", baixo_risco)
        kpi2.metric("Risco de Suicídio (Seguro)", risco_suicidio_kpi, delta="Vigilância Máxima", delta_color="inverse")
        kpi3.metric("Isolamento Médico (TB/Surtos)", infeccao_kpi, delta="Risco de Contágio", delta_color="inverse")
        kpi4.metric("Economia Potencial/Mês", f"R$ {economia_potencial:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        st.markdown("---")
        st.markdown("### 🗂️ Matriz de Gestão Carcerária Integrada")
        
        df_unificado = pd.DataFrame()
        if not df_risco.empty or not df_saude.empty:
            if not df_risco.empty and not df_saude.empty:
                df_unificado = pd.merge(df_risco, df_saude, on='matricula', how='outer')
            elif not df_risco.empty:
                df_unificado = df_risco.copy()
            else:
                df_unificado = df_saude.copy()
                df_unificado['nome'] = "Desconhecido"

            df_unificado.fillna("-", inplace=True)
            
            df_display = df_unificado.rename(columns={
                'nome': 'Custodiado', 'matricula': 'Matrícula', 'faixa_risco': 'Parecer Jurídico',
                'laudo_pclr': 'Psicopatia', 'risco_suicidio': 'Risco Suicídio', 
                'risco_psicose': 'Psicose', 'alerta_infeccao': 'Infecção'
            })
            
            if 'score_total' in df_display.columns:
                df_display = df_display.drop(columns=['score_total'])
                
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.markdown("### 📄 Exportar Dossiê Eletrônico Completo (PDF)")
        st.write("Gere um relatório unificado contendo os laudos clínicos, psiquiátricos e atuariais do custodiado.")
        
        if not df_unificado.empty:
            lista_matriculas = df_unificado['matricula'].dropna().unique().tolist()
            mat_selecionada = st.selectbox("Selecione a Matrícula do Custodiado:", [""] + lista_matriculas)
            
            if mat_selecionada:
                pdf_dossie_bytes = gerar_dossie_completo_pdf(mat_selecionada)
                if pdf_dossie_bytes:
                    st.download_button(
                        label=f"📥 Baixar Dossiê Completo - Matrícula {mat_selecionada}",
                        data=pdf_dossie_bytes,
                        file_name=f"Dossie_Unificado_ORION_{mat_selecionada}.pdf",
                        mime="application/pdf"
                    )