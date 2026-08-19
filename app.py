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

def salvar_avaliacao_completa(nome, matricula, score_juridico, faixa_risco, memoria, score_pclr, laudo_pclr, sui, psi, inf):
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO saude_integrada (nome, matricula, score_pclr, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao, data_avaliacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nome, matricula, score_pclr, laudo_pclr, sui, psi, inf, data_hoje))
    
    cursor.execute('''
        INSERT INTO avaliacao_risco (nome, matricula, score_total, faixa_risco, memoria_calculo, data_avaliacao)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nome, matricula, score_juridico, faixa_risco, json.dumps(memoria), data_hoje))
    
    conexao.commit()
    conexao.close()

def buscar_dados_custodiado(matricula):
    conexao = sqlite3.connect('orion_pen.db')
    cursor = conexao.cursor()
    cursor.execute("SELECT nome FROM avaliacao_risco WHERE matricula = ? ORDER BY id DESC LIMIT 1", (matricula,))
    risco = cursor.fetchone()
    conexao.close()
    return risco[0] if risco else ""

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

# PDF: Dossiê Unificado (Substitui os antigos)
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

    nome_custodiado = risco[0] if risco else "Não Informado"
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
        
        pdf.ln(3)
        pdf.set_font("helvetica", style="B", size=9)
        pdf.set_text_color(100, 100, 100) 
        pdf.cell(0, 5, "FONTES E PROTOCOLOS CIENTÍFICOS APLICADOS:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=8)
        pdf.multi_cell(0, 4, "- PCL-R (Hare Psychopathy Checklist-Revised): Padrão-ouro global para predição de reincidência violenta e psicopatia criminal.", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, "- C-SSRS (Columbia-Suicide Severity Rating Scale): Protocolo oficial de triagem endossado pela OMS e pelo FDA.", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, "- Triagem BPRS-A (Brief Psychiatric Rating Scale): Matriz avaliativa para quadros psicóticos e conversão penal.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0) 
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
            pdf.multi_cell(0, 6, f"Base Legal: {item['fonte_legal']}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 6, f"Justificativa: {item['justificativa']}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    pdf.ln(5)
    pdf.set_font("helvetica", style="I", size=9)
    pdf.multi_cell(0, 5, "TERMO DE CONFORMIDADE: Dossiê gerado eletronicamente integrando as bases clínicas e atuariais. Cálculos travados sistemicamente. Decisão final judicial.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

# ==========================================
# 3. CAMADA DE APRESENTAÇÃO E NAVEGAÇÃO
# ==========================================
st.set_page_config(page_title="ORION-Pen", layout="wide")
st.sidebar.title("⚖️ ORION-Pen")
menu = st.sidebar.radio("Navegação do Sistema:", ["📝 Avaliação Integrada (Intake)", "📊 Painel da Gestão (BI)"])
st.sidebar.markdown("---")
st.sidebar.info("Proteção Legal: Arquitetura White-Box Ativa (Anti-Fraude)")

# ==========================================
# MÓDULO 1: INTAKE UNIFICADO (Saúde + Jurídico)
# ==========================================
if menu == "📝 Avaliação Integrada (Intake)":
    st.title("Formulário de Entrevista Técnica Integrada")
    st.info("Fluxo Único: Os dados clínicos calculados geram a nota jurídica automaticamente (Sistema Anti-Fraude).")
    
    matricula = st.text_input("🔍 Matrícula / Prontuário (Digite e pressione Enter):")
    nome_sugerido = buscar_dados_custodiado(matricula) if matricula else ""
    if nome_sugerido:
        st.success("✅ Prontuário localizado na base de dados!")

    nome = st.text_input("Nome do Custodiado:", value=nome_sugerido)
    
    st.markdown("---")
    st.write("### I. Triagem de Saúde Mental (Motor PCL-R)")
    st.write("Responda ao inventário clínico. A nota será calculada e travada sistemicamente.")
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
    st.write("### II. Triagem Clínica de Crise")
    sui_1 = st.selectbox("Expressou desejo de estar morto ou tem plano de suicídio? (C-SSRS)", ["Não", "Sim"])
    psi_1 = st.selectbox("Apresenta delírios ou alucinações severas? (BPRS-A)", ["Não", "Sim (Incompatível com Sistema Comum)"])
    inf_1 = st.selectbox("Apresenta tosse persistente, sarna ou suspeita de vírus?", ["Não", "Sim"])

    st.markdown("---")
    st.write("### III. Fatores Jurídicos Estáticos e Dinâmicos")
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
        
        val_faccao = st.selectbox("5. Pertencimento a facção com lastro documental?", ["Não", "Sim"])
        just_faccao = st.text_area("Justificativa e Fonte Documental (Fator 5):", placeholder="Ex: O Relatório de Inteligência Penitenciária nº 12/2026 aponta ausência de vínculos ativos...")
        
        val_trabalho = st.selectbox("8. Engajado formalmente visando remição?", ["Não", "Sim (Reduz Risco)"])
        just_trabalho = st.text_area("Justificativa (Fator 8):", placeholder="Ex: Declaração do setor de laborterapia comprova trabalho regular na manutenção predial...")

    with col_est2:
        val_reincidencia = st.selectbox("3. Possui reincidência com trânsito em julgado?", ["Não", "Sim"])
        just_reincidencia = st.text_area("Justificativa (Fator 3):", placeholder="Ex: A certidão de antecedentes criminais atualizada demonstra ausência de condenações...")
        
        val_fuga = st.selectbox("4. Histórico registrado de evasão ou falta grave (fuga)?", ["Não", "Sim"])
        just_fuga = st.text_area("Justificativa (Fator 4):", placeholder="Ex: O prontuário disciplinar da unidade não registra Processos Administrativos Disciplinares (PADs)...")

        val_quimica = st.selectbox("6. Avaliação clínica formal indica dependência química?", ["Não", "Sim"])
        just_quimica = st.text_area("Justificativa (Fator 6):", placeholder="Ex: A avaliação psicossocial atesta uso abusivo de entorpecentes, havendo recomendação...")
        
        val_disciplina = st.selectbox("7. Faltas disciplinares graves nos últimos 12 meses?", ["Não", "Sim"])
        just_disciplina = st.text_area("Justificativa (Fator 7):", placeholder="Ex: O Boletim Informativo (BI) da unidade atesta bom comportamento carcerário...")

    if st.button("Salvar Avaliação Integrada e Gerar Dossiê"):
        campos_justificativa = {
            "Fator 1 (Iniciação)": just_iniciacao, "Fator 2 (Natureza)": just_natureza,
            "Fator 3 (Reincidência)": just_reincidencia, "Fator 4 (Fuga)": just_fuga, 
            "Fator 5 (Facção)": just_faccao, "Fator 6 (Dep. Química)": just_quimica, 
            "Fator 7 (Disciplina)": just_disciplina, "Fator 8 (Trabalho)": just_trabalho
        }
        erros_tamanho = [nome_campo for nome_campo, texto in campos_justificativa.items() if len(texto.strip()) < 50]
        
        if not nome or not matricula:
            st.error("Erro: Preencha o nome e a matrícula.")
        elif erros_tamanho:
            st.error("⚠️ **Erro de Compliance:** Os seguintes campos não atingiram o detalhamento mínimo (50 caracteres):")
            for erro in erros_tamanho: st.write(f"- {erro}")
        else:
            # 1. MOTOR CLÍNICO (CALCULADO INVISIVELMENTE)
            score_pclr_parcial = (opcoes_pontos[i1] + opcoes_pontos[i2] + opcoes_pontos[i3] + opcoes_pontos[i4] + opcoes_pontos[i5] + 
                                 opcoes_pontos[i6] + opcoes_pontos[i7] + opcoes_pontos[i8] + opcoes_pontos[i9] + opcoes_pontos[i10])
            score_pclr_final = score_pclr_parcial * 2 
            
            if score_pclr_final >= 30:
                laudo_pclr = "ALTO RISCO (Alta Compatibilidade com Psicopatia)"
                peso_clinico = 45.0
            elif score_pclr_final >= 20:
                laudo_pclr = "MÉDIO RISCO (Presença de Traços Antissociais)"
                peso_clinico = 20.0
            else:
                laudo_pclr = "BAIXO RISCO (Traços Psicopáticos Inexpressivos)"
                peso_clinico = 0.0
                
            risco_suicidio = "ALTO RISCO (Alerta Vermelho)" if sui_1 == "Sim" else "Baixo/Nenhum Risco"
            risco_psicose = "ALERTA PSICÓTICO (Sugerir HCTP)" if "Sim" in psi_1 else "Sem traços psicóticos"
            alerta_infeccao = "SIM (Isolamento Necessário)" if inf_1 == "Sim" else "Liberado (Apto para Galeria)"
            
            # Automação da Justificativa para blindar o documento contra a Defesa
            just_psicopatia_automatica = f"Triagem estruturada indicativa (Score PCL-R: {score_pclr_final}/40). Cálculo processado sistemicamente com base nas diretrizes do protocolo clínico preenchidas pelo operador da unidade."

            # 2. MOTOR JURÍDICO
            fatores = [
                FatorRisco("CLI-01", f"Perfil: {laudo_pclr}", "clinico", peso_clinico, "PCL-R", 1.0, just_psicopatia_automatica),
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
            
            # 3. SALVAMENTO E EXPORTAÇÃO
            salvar_avaliacao_completa(nome, matricula, resultado['score_total'], resultado['faixa_risco'], resultado['memoria_calculo'], score_pclr_final, laudo_pclr, risco_suicidio, risco_psicose, alerta_infeccao)
            
            st.success(f"✅ Dossiê de {nome} salvo com sucesso! (Score Total: {resultado['score_total']})")
            
            pdf_bytes = gerar_dossie_completo_pdf(matricula)
            if pdf_bytes:
                st.download_button("📥 Baixar Dossiê Completo (PDF)", pdf_bytes, f"Dossie_ORION_{matricula}.pdf", "application/pdf")

# ==========================================
# MÓDULO 2: PAINEL DA GESTÃO (BI)
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
        if not df_risco.empty and not df_saude.empty:
            df_unificado = pd.merge(df_risco, df_saude, on='matricula', how='outer')
        elif not df_risco.empty:
            df_unificado = df_risco.copy()
        elif not df_saude.empty:
            df_unificado = df_saude.copy()
            df_unificado['nome'] = "Desconhecido"

        if not df_unificado.empty:
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
            st.markdown("### 📄 Exportar Dossiê Eletrônico Completo")
            lista_matriculas = df_unificado['matricula'].dropna().unique().tolist()
            mat_selecionada = st.selectbox("Selecione a Matrícula:", [""] + lista_matriculas)
            
            if mat_selecionada:
                pdf_bytes = gerar_dossie_completo_pdf(mat_selecionada)
                if pdf_bytes:
                    st.download_button(f"📥 Baixar Dossiê - Matrícula {mat_selecionada}", pdf_bytes, f"Dossie_{mat_selecionada}.pdf", "application/pdf")
