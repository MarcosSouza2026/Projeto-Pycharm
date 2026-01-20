import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL, callback_context
import pandas as pd
import dash_bootstrap_components as dbc
import json
import os
import base64
import flask
from flask import send_from_directory
import dash_quill
from datetime import datetime

# --- 1. CONFIGURAÇÕES E DADOS ---
CSV_FILE = 'instalacoes.csv'
CSV_AGENDA = 'agenda_tecnicos.csv'
CSV_KITS = 'kits_estoque.csv'
NOTAS_FILE = 'notas_base.json'
FOLDER_FILES = 'arquivos_base'

if not os.path.exists(CSV_AGENDA):
    pd.DataFrame(columns=COLUNAS).to_csv(CSV_AGENDA, index=False, sep=',', encoding='latin-1')

if not os.path.exists(FOLDER_FILES):
    os.makedirs(FOLDER_FILES)

# COLUNAS ORIGINAIS + VALOR ACORDADO
COLUNAS = ['id_instalacao', 'tecnico', 'descricao', 'data_inicio', 'status', 'materiais_checklist', 'mes_referencia',
           'responsavel', 'telefone', 'observacoes', 'valor_acordado']
LISTA_TECNICOS = ['Giovanni', 'Roberto', 'Pedro', 'Jobert', 'Leonardo', 'Gustavo', 'Valdeci', 'Farley']

MESES_PT = {
    "January": "Janeiro", "February": "Fevereiro", "March": "Março", "April": "Abril",
    "May": "Maio", "June": "Junho", "July": "Julho", "August": "Agosto",
    "September": "Setembro", "October": "Outubro", "November": "Novembro", "December": "Dezembro"
}


def init_csv():
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=COLUNAS).to_csv(CSV_FILE, index=False, sep=',', encoding='latin-1')
    else:
        df = pd.read_csv(CSV_FILE, sep=',', encoding='latin-1')
        if 'valor_acordado' not in df.columns:
            df['valor_acordado'] = ""
            df.to_csv(CSV_FILE, index=False, sep=',', encoding='latin-1')

    if not os.path.exists(CSV_KITS):
        pd.DataFrame(columns=['tecnico', 'item', 'qtd_tem', 'qtd_faltante']).to_csv(CSV_KITS, index=False, sep=',',
                                                                                    encoding='latin-1')


def load_data():
    if not os.path.exists(CSV_FILE): return pd.DataFrame(columns=COLUNAS)
    try:
        df = pd.read_csv(CSV_FILE, sep=',', encoding='latin-1', dtype={'id_instalacao': str})
        for col in COLUNAS:
            if col not in df.columns: df[col] = ""
        return df.fillna("")
    except:
        return pd.DataFrame(columns=COLUNAS)


init_csv()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    # Isso garante que o app se ajuste à tela do celular:
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# 2. ESSA LINHA É A MAIS IMPORTANTE PARA A NUVEM:
server = app.server


@app.server.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(FOLDER_FILES, filename, as_attachment=False)


def salvar_nota_json(conteudo):
    with open(NOTAS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'conteudo': conteudo}, f)


def carregar_nota_json():
    if os.path.exists(NOTAS_FILE):
        with open(NOTAS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('conteudo', '')
    return ""


def gerar_lista_arquivos(lista):
    return html.Ul([
        html.Li(
            html.Button(f, id={'type': 'btn-ver-arquivo', 'filename': f},
                        className="btn btn-link btn-sm text-info p-0 text-start",
                        style={'textDecoration': 'none', 'fontSize': '12px'}),
            className="mb-1"
        ) for f in lista
    ], style={'listStyle': 'none', 'padding': '0'})


# --- NAVBAR ---
navbar = dbc.Navbar(
    dbc.Container([
        html.A(dbc.Row([
            dbc.Col(html.Img(src="/assets/logo.png", height="45px"), width="auto"),
            dbc.Col(dbc.NavbarBrand("LOGÍSTICA MAXVEL", className="ms-3 fw-bold text-info"), width="auto"),
        ], align="center", className="g-0"), href="/", style={"textDecoration": "none"}),
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(html.I(className="bi bi-search")),
                    dbc.Input(id="search-input", placeholder="O.S + Enter...", type="text", style={"width": "200px"},
                              debounce=True),
                ], size="sm")
            ])
        ], className="ms-auto me-3 d-none d-md-flex"),
        dbc.Nav([
            dbc.NavItem(
                dbc.Button([html.I(className="bi bi-plus-lg me-2"), "Nova O.S"], id='btn-novo', color="info", size="sm",
                           className="fw-bold")),
            dbc.NavItem(dcc.Dropdown(id='filtro-mes', style={'color': '#000', 'width': '180px'}, clearable=False,
                                     className="ms-3")),
        ], navbar=True)
    ], fluid=True),
    color="dark", dark=True, className="mb-0 shadow-sm border-bottom border-info py-2 sticky-top"
)

# --- MODAIS ---
modal_principal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Gerenciar Ordem de Serviço")),
    dbc.ModalBody([
        dcc.Store(id='modal-id-store'),
        dcc.Store(id='temp-items-store', data=[]),
        dcc.Store(id='store-index-item-deletar'),
        dbc.Row([
            dbc.Col([dbc.Label("Número da O.S:"), dbc.Input(id='modal-id-manual', type='text')], width=4),
            dbc.Col([dbc.Label("Descrição:"), dbc.Input(id='modal-desc', type='text')], width=8),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Responsável:"), dbc.Input(id='modal-resp', type='text')], width=5),
            dbc.Col([dbc.Label("Telefone:"), dbc.Input(id='modal-tel', type='text')], width=4),
            dbc.Col([dbc.Label("Valor Acordado:"), dbc.Input(id='modal-valor', type='text', placeholder="R$ 0,00")],
                    width=3),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Técnico:"),
                     dcc.Dropdown(id='modal-tec', options=[{'label': t, 'value': t} for t in LISTA_TECNICOS],
                                  style={'color': '#000'})], width=6),
            dbc.Col([dbc.Label("Status:"), dbc.Select(id='modal-status', options=[
                {"label": "Aberto", "value": "Aberto"}, {"label": "Em Andamento", "value": "Em Andamento"},
                {"label": "Finalizada", "value": "Finalizada"}
            ])], width=3),
            dbc.Col([dbc.Label("Data/Hora:"), dbc.Input(id='modal-data', type='datetime-local')], width=3),
        ], className="mb-3"),
        dbc.Label("Observações:"),
        dbc.Textarea(id='modal-obs', style={"height": "70px"}, className="mb-3"),
        html.Hr(),
        html.H6("Materiais", className="text-info"),
        dbc.Row([
            dbc.Col(dbc.Input(id='input-lista', placeholder="Item..."), width=6),
            dbc.Col(dbc.Input(id='input-qtd', type='number', value=1), width=2),
            dbc.Col(dbc.Button("Add", id="btn-gerar", color="info", outline=True), width=3),
            dbc.Col(dbc.Button(html.I(className="bi bi-trash"), id="btn-abrir-clear", color="link",
                               className="text-warning p-0"), width=1),
        ], className="g-2 mb-3 align-items-end"),
        html.Div(id='lista-materiais-container', style={"maxHeight": "200px", "overflowY": "auto"})
    ]),
    dbc.ModalFooter([
        dbc.Button("Excluir", id="btn-abrir-confirm", color="danger", size="sm", outline=True, className="me-auto"),
        dbc.Button("Fechar", id="btn-fechar", color="secondary", size="sm"),
        dbc.Button("Salvar", id="btn-salvar", color="success", size="sm", className="px-4"),
    ]),
], id="main-modal", is_open=False, size="lg")

# --- COLOQUE ISSO AQUI (ANTES DO APP.LAYOUT) ---
modal_manutencao_simples = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Gerenciar Manutenção"), className="bg-primary text-white"),
    dbc.ModalBody([
        # --- ESSA LINHA É ESSENCIAL PARA NÃO DAR ERRO ---
        dcc.Store(id="modo-modal-agenda", data="novo"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Número da O.S:"),
                dbc.Input(id="os-manutencao", type="text"),
            ], width=4),
            dbc.Col([
                dbc.Label("Nome do Cliente:"),
                dbc.Input(id="nome-manutencao", type="text"),
            ], width=8),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Telefone:"),
                dbc.Input(id="tel-manutencao", type="text"),
            ], width=6),
            dbc.Col([
                dbc.Label("Técnico:"),
                dcc.Dropdown(
                    id="tec-manutencao",
                    options=[{'label': t, 'value': t} for t in LISTA_TECNICOS]
                ),
            ], width=6),
        ], className="mb-3"),

        dbc.Label("Status da Manutenção:"),
        html.Div([  # <-- Verifique se esta linha está alinhada com o dbc.Label acima
            dbc.RadioItems(
                id="status-manutencao",
                options=[
                    {"label": "Aberto", "value": "Aberto"},
                    {"label": "Finalizada", "value": "Finalizada"},
                    {"label": "Pendência", "value": "Pendência"},
                ],
                value="Aberto",
                inline=True,
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary me-2",
                labelCheckedClassName="active",
            ),
        ], className="mb-3"),  # <-- Verifique se este fechamento também está alinhado

        dbc.Label("Descrição/Problema:"),
        dbc.Textarea(id="desc-manutencao", style={"height": "70px"}, className="mb-3"),
    ]),
    dbc.ModalFooter([
        dbc.Button("Excluir", id="btn-excluir-agenda", color="danger", outline=True, className="me-auto"),
        dbc.Button("Cancelar", id="fechar-manutencao-simples", color="secondary"),
        dbc.Button("Salvar", id="salvar-manutencao-simples", color="success")
    ]),
], id="modal-simples-id", is_open=False, size="lg")
modal_agenda = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Novo Agendamento de Manutenção")),
    dbc.ModalBody([
        dcc.Store(id='agenda-id-store'),
        dbc.Row([
            dbc.Col([dbc.Label("Nº O.S:"), dbc.Input(id='agenda-id-manual', type='text')], width=4),
            dbc.Col([dbc.Label("Cliente:"), dbc.Input(id='agenda-cliente', type='text')], width=8),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Telefone:"), dbc.Input(id='agenda-tel', type='text')], width=6),
            dbc.Col([dbc.Label("Técnico:"),
                     dcc.Dropdown(id='agenda-tec', options=[{'label': t, 'value': t} for t in LISTA_TECNICOS],
                                  style={'color': '#000'})], width=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Status:"), dbc.Select(id='agenda-status', options=[
                {"label": "Pendente", "value": "Pendente"},
                {"label": "Não Atendimento", "value": "Não Atendimento"},
                {"label": "Resolvido", "value": "Resolvido"}
            ])], width=6),
            dbc.Col([dbc.Label("Data/Hora:"), dbc.Input(id='agenda-data', type='datetime-local')], width=6),
        ], className="mb-3"),
        dbc.Label("Problema Reclamado:"),
        dbc.Textarea(id='agenda-obs', style={"height": "100px"}, className="mb-3"),

        # Caixa de informações de encerramento (aparece se for resolvido)
        html.Div([
            dbc.Label("Informações de Encerramento:"),
            dbc.Textarea(id='agenda-info-final', placeholder="Descreva como foi resolvido...")
        ], id="div-info-final", style={"display": "none"})
    ]),
    dbc.ModalFooter([
        dbc.Button("Fechar", id="agenda-btn-fechar", color="secondary", size="sm"),
        dbc.Button("Salvar Manutenção", id="agenda-btn-salvar", color="success", size="sm"),
    ]),
], id="modal-agenda", is_open=False, size="lg")

modal_pergunta_finalizar = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Finalizar O.S")),
    dbc.ModalBody([dbc.Textarea(id='input-obs-final', placeholder="Observação de fechamento...")]),
    dbc.ModalFooter([dbc.Button("Voltar", id="btn-cancel-final-obs"),
                     dbc.Button("Salvar e Finalizar", id="btn-confirm-final-obs", color="success")]),
], id="modal-pergunta-finalizar", is_open=False, centered=True)

confirm_modal_inst = dbc.Modal([
    dbc.ModalHeader("Excluir Registro?"),
    dbc.ModalFooter(
        [dbc.Button("Sim", id="btn-excluir-confirmado", color="danger"), dbc.Button("Não", id="btn-excluir-cancelar")]),
], id="confirm-modal", is_open=False, centered=True)

confirm_clear_all = dbc.Modal([
    dbc.ModalHeader("Limpar materiais?"),
    dbc.ModalFooter([dbc.Button("Sim", id="btn-clear-sim", color="danger"), dbc.Button("Não", id="btn-clear-nao")]),
], id="modal-conf-clear", is_open=False, centered=True)

modal_conf_item_unico = dbc.Modal([
    dbc.ModalHeader("Remover item?"),
    dbc.ModalFooter([dbc.Button("Remover", id="btn-confirm-del-item", color="danger"),
                     dbc.Button("Cancelar", id="btn-cancel-del-item")]),
], id="modal-item-unico", is_open=False, centered=True)

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    html.Div(style={'position': 'fixed', 'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)',
                    'backgroundImage': 'url("/assets/logo.png")', 'backgroundRepeat': 'no-repeat',
                    'backgroundPosition': 'center', 'backgroundSize': 'contain', 'width': '60vw', 'height': '60vh',
                    'opacity': '0.04', 'zIndex': '0', 'pointerEvents': 'none'}),
    navbar,
    dbc.Container([
        dbc.Tabs([
            dbc.Tab(label="Gestão de O.S.", tab_id="tab-os", label_class_name="fw-bold text-info"),
            dbc.Tab(label="Kit de Manutenção", tab_id="tab-kit", label_class_name="fw-bold text-info"),
            dbc.Tab(label="Base de Conhecimento", tab_id="tab-base", label_class_name="fw-bold text-info"),
            dbc.Tab(label="Agenda Técnicos", tab_id="tab-agenda", label_class_name="fw-bold text-info"),

        ], id="tabs-principal", active_tab="tab-os", className="mt-3 mb-4"),
        html.Div(id="conteudo-aba"),
        dcc.Store(id='refresh-signal', data=0),
        dcc.Store(id='refresh-kit-signal', data=0),
        modal_principal, modal_pergunta_finalizar, confirm_modal_inst, confirm_clear_all, modal_conf_item_unico,
        # No final do seu app.layout, adicione a variável que criamos acima:

    ], fluid=True),
    modal_principal,
    modal_pergunta_finalizar,
    confirm_modal_inst,
    modal_manutencao_simples,  # Agora o Python já sabe o que é isso!
], style={"backgroundColor": "#121212", "minHeight": "100vh"})

# --- NOVO MODAL DE MANUTENÇÃO SIMPLES ---
modal_manutencao_simples = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Nova Manutenção - Cadastro Rápido")),
    dbc.ModalBody([
        dbc.Label("Nome do Cliente:"),
        dbc.Input(id="nome-manutencao-simples", placeholder="Digite o nome...", type="text"),
        html.Br(),
        dbc.Label("Descrição do Problema:"),
        dbc.Textarea(id="desc-manutencao-simples", placeholder="O que aconteceu?")
    ]),
    dbc.ModalFooter([
        dbc.Button("Fechar", id="fechar-manutencao-simples", color="secondary"),
        dbc.Button("Salvar", id="salvar-manutencao-simples", color="success")
    ]),
], id="modal-simples-id", is_open=False)


# --- RENDERIZAÇÃO ABAS ---
def render_aba_os():
    return dbc.Container([dcc.Loading(
        html.Div(id='cards-area', className='row row-cols-1 row-cols-md-2 row-cols-lg-3 row-cols-xl-4 g-4'), type="dot",
        color="#0dcaf0")], fluid=True)


def render_aba_kit():
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Checklist Kit Permanente (Ferramentas)", className="mb-0 text-info")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([dbc.Label("Técnico:"), dcc.Dropdown(id='dropdown-kit-tec',
                                                                         options=[{'label': t, 'value': t} for t in
                                                                                  LISTA_TECNICOS],
                                                                         placeholder="Selecione...",
                                                                         style={'color': '#000'})], width=4),
                            dbc.Col(id="resumo-kit-col", width=5),
                            dbc.Col(
                                [dbc.Button([html.I(className="bi bi-save me-2"), "Salvar Kit"], id="btn-salvar-kit",
                                            color="success", className="mt-4")], width=3, className="text-end")
                        ], className="mb-4 align-items-end"),
                        html.Div(id='tabela-kit-container')
                    ])
                ], color="dark", outline=True, className="border-info shadow")
            ], width=12)
        ])
    ], className="p-2")


def render_aba_base():
    conteudo_salvo = carregar_nota_json()
    arquivos_lista = os.listdir(FOLDER_FILES)
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Documentação e Senhas", className="text-info mb-0")),
                    dbc.CardBody([
                        html.Div([dash_quill.Quill(id='editor-texto', value=conteudo_salvo, modules={
                            'toolbar': [['bold', 'italic', 'underline'], [{'list': 'ordered'}, {'list': 'bullet'}],
                                        ['link']]})],
                                 style={'height': '350px', 'backgroundColor': 'white', 'color': 'black',
                                        'marginBottom': '50px'}),
                        dbc.Button("Salvar Documentação", id="btn-salvar-base", color="success", className="mt-3")
                    ])
                ], color="dark", outline=True, className="border-info")
            ], width=5),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Anexos e Visualizador", className="text-info mb-0")),
                    dbc.CardBody([
                        dcc.Upload(id='upload-base', children=html.Div(['Arraste ou ', html.A('Selecione')]),
                                   style={'width': '100%', 'height': '40px', 'lineHeight': '40px', 'borderWidth': '1px',
                                          'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center',
                                          'marginBottom': '10px'}, multiple=True),
                        dbc.Row([
                            dbc.Col([html.H6("Arquivos:", className="small text-muted"),
                                     html.Div(id='lista-arquivos-base', children=gerar_lista_arquivos(arquivos_lista),
                                              style={'maxHeight': '400px', 'overflowY': 'auto'})], width=4),
                            dbc.Col([html.H6("Visualização:", className="small text-muted"),
                                     html.Iframe(id='visualizador-frame',
                                                 style={'width': '100%', 'height': '400px', 'border': '1px solid #444',
                                                        'backgroundColor': '#fff'})], width=8)
                        ])
                    ])
                ], color="dark", outline=True, className="border-info")
            ], width=7)
        ])
    ], className="p-3")


# --- CALLBACKS GERAIS ---
@app.callback(Output("conteudo-aba", "children"), Input("tabs-principal", "active_tab"))
def alternar_abas(tab_ativa):
    if tab_ativa == "tab-kit": return render_aba_kit()
    if tab_ativa == "tab-base": return render_aba_base()
    if tab_ativa == "tab-agenda":
        # Retorna a estrutura da agenda com IDs exclusivos
        return html.Div([
            dbc.Tabs([
                dbc.Tab(label="DIVINÓPOLIS", tab_id="ag-div"),
                dbc.Tab(label="ITAÚNA", tab_id="ag-ita"),
            ], id="tabs-agenda-cidades", active_tab="ag-div", className="mb-3"),
            dbc.Row([
                dbc.Col(
                    dbc.Button([html.I(className="bi bi-plus-circle me-2"), "Nova Manutenção"], id="btn-nova-agenda",
                               color="success"), width="auto")
            ], justify="end", className="mb-3"),
            # ESTE ID ABAIXO TEM QUE SER DIFERENTE DO DA ABA PRINCIPAL
            dcc.Loading(html.Div(id="cards-agenda-area", className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4"),
                        type="dot")
        ])
    return render_aba_os()


# --- CALLBACKS KIT ---
@app.callback(Output('tabela-kit-container', 'children'),
              [Input('dropdown-kit-tec', 'value'), Input('refresh-kit-signal', 'data')])
def carregar_tabela_kit(tecnico, sig):
    if not tecnico: return html.Div("Selecione um técnico.", className="text-muted text-center py-5")
    itens = ["BATERIA 7A", "BATERIA SENSOR 8000", "BATERIA SENSOR 8000 JANELA", "CABO BIPOLAR", "CABO DE 6 VIAS",
             "CÂMERA 2 MP ANALÓGICA", "CONECTOR BNC", "CONECTOR P4", "MÓDULO GPRS INTELBRAS 8000", "MÓDULO ETHERNET",
             "MÓDULO GPRS 3G JFL", "SENSOR 8000 JANELA", "SENSOR 8000 INTERNO", "SENSOR DSE 830", "SENSOR IDX 1001",
             "SENSOR SEMI ABERTO IRD 640 JFL", "FONTE 10A", "SIRENE"]
    df_kits = pd.read_csv(CSV_KITS, sep=',', encoding='latin-1')
    dados_tec = df_kits[df_kits['tecnico'] == tecnico]
    rows = []
    for i, item in enumerate(itens):
        ext = dados_tec[dados_tec['item'] == item]
        q_t, q_f = (ext.iloc[0]['qtd_tem'], ext.iloc[0]['qtd_faltante']) if not ext.empty else (0, 0)
        sw = [1] if q_f == 0 and q_t > 0 else []
        rows.append(html.Tr([
            html.Td(dbc.Checklist(options=[{"label": "", "value": 1}], value=sw, id={'type': 'kit-switch', 'index': i},
                                  switch=True)),
            html.Td(html.Span(item, id={'type': 'kit-item-nome', 'index': i}), className="fw-bold"),
            html.Td(dbc.Input(type="number", value=q_t, id={'type': 'kit-qtd-tem', 'index': i}, size="sm",
                              style={"width": "80px", "backgroundColor": "#2b2b2b", "color": "white"})),
            html.Td(dbc.Input(type="number", value=q_f, id={'type': 'kit-qtd-falta', 'index': i}, size="sm",
                              style={"width": "80px", "backgroundColor": "#2b2b2b", "color": "#ff4d4d"})),
        ]))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Status"), html.Th("Nome do Item"), html.Th("Qtd. Atual"), html.Th("Faltante")]),
                    className="table-secondary"), html.Tbody(rows)], bordered=True, hover=True, color="dark",
        striped=True)


@app.callback([Output('btn-salvar-kit', 'children'), Output('refresh-kit-signal', 'data')],
              Input('btn-salvar-kit', 'n_clicks'),
              [State('dropdown-kit-tec', 'value'), State({'type': 'kit-item-nome', 'index': ALL}, 'children'),
               State({'type': 'kit-qtd-tem', 'index': ALL}, 'value'),
               State({'type': 'kit-qtd-falta', 'index': ALL}, 'value'), State('refresh-kit-signal', 'data')],
              prevent_initial_call=True)
def salvar_dados_kit(n, tec, nomes, qs_t, qs_f, sig):
    if not tec: return dash.no_update
    df = pd.read_csv(CSV_KITS, sep=',', encoding='latin-1')
    df = df[df['tecnico'] != tec]
    novos = [{'tecnico': tec, 'item': n, 'qtd_tem': t if t else 0, 'qtd_faltante': f if f else 0} for n, t, f in
             zip(nomes, qs_t, qs_f)]
    pd.concat([df, pd.DataFrame(novos)]).to_csv(CSV_KITS, index=False, sep=',', encoding='latin-1')
    return [html.I(className="bi bi-check-circle me-2"), "Kit Salvo!"], (sig or 0) + 1


# --- CALLBACKS GESTÃO O.S. (TRAVA DEFINITIVA DE MODAIS) ---
@app.callback(
    [Output("confirm-modal", "is_open"),
     Output("modal-conf-clear", "is_open"),
     Output("modal-item-unico", "is_open"),
     Output("modal-pergunta-finalizar", "is_open"),
     Output("store-index-item-deletar", "data")],
    [Input("btn-abrir-confirm", "n_clicks"),
     Input("btn-abrir-clear", "n_clicks"),
     Input({"type": "btn-del-single", "index": ALL}, "n_clicks"),
     Input("btn-salvar", "n_clicks"),
     Input("btn-excluir-confirmado", "n_clicks"),
     Input("btn-clear-sim", "n_clicks"),
     Input("btn-confirm-del-item", "n_clicks"),
     Input("btn-confirm-final-obs", "n_clicks"),
     Input("btn-excluir-cancelar", "n_clicks"),
     Input("btn-clear-nao", "n_clicks"),
     Input("btn-cancel-del-item", "n_clicks"),
     Input("btn-cancel-final-obs", "n_clicks")],
    [State("modal-status", "value")],
    prevent_initial_call=True
)
def toggle_all_confirms(n_conf, n_clear, n_single, n_save, n_ex_c, n_cl_s, n_it_c, n_fi_c, n_ex_n, n_cl_n, n_it_n,
                        n_fi_n, status_atual):
    ctx = callback_context
    if not ctx.triggered: return False, False, False, False, dash.no_update

    trig_id = ctx.triggered[0]['prop_id']

    # SÓ ABRE SE O N_CLICKS EXISTIR E FOR MAIOR QUE ZERO (TRAVA REAL)
    if "btn-abrir-confirm.n_clicks" in trig_id and n_conf: return True, False, False, False, dash.no_update
    if "btn-abrir-clear.n_clicks" in trig_id and n_clear: return False, True, False, False, dash.no_update

    if "btn-del-single" in trig_id:
        val = ctx.triggered[0]['value']
        if val:
            idx = json.loads(trig_id.split('.')[0])['index']
            return False, False, True, False, idx

    if "btn-salvar.n_clicks" in trig_id and n_save and status_atual == "Finalizada":
        return False, False, False, True, dash.no_update

    return False, False, False, False, None


@app.callback(
    [Output("main-modal", "is_open"),
     Output('modal-id-store', 'data'),
     Output('modal-id-manual', 'value'),
     Output('modal-desc', 'value'),
     Output('modal-tec', 'value'),
     Output('modal-data', 'value'),
     Output('temp-items-store', 'data', allow_duplicate=True),
     Output('modal-status', 'value'),
     Output('modal-resp', 'value'),
     Output('modal-tel', 'value'),
     Output('modal-obs', 'value'),
     Output('modal-valor', 'value'),
     Output('input-obs-final', 'value')],
    [Input('btn-novo', 'n_clicks'),
     Input({'type': 'edit', 'id': ALL}, 'n_clicks'),
     Input('btn-salvar', 'n_clicks'),
     Input('btn-confirm-final-obs', 'n_clicks'),
     Input('btn-fechar', 'n_clicks'),
     Input('btn-excluir-confirmado', 'n_clicks')],
    [State('modal-status', 'value')],
    prevent_initial_call=True
)
def manage_main(n_novo, n_edit, n_s, n_confirm_f, n_f, n_ex, status_atual):
    ctx = callback_context
    if not ctx.triggered:
        return [dash.no_update] * 13

    trig_id = ctx.triggered[0]['prop_id']

    # 1. Lógica para Editar O.S. Existente
    # 1. Lógica para Editar O.S. Existente
    if "edit" in trig_id:
        try:
            # Pega a parte do ID antes do '.n_clicks' e limpa espaços
            clean_id = trig_id.split('.n_clicks')[0]
            tid_dict = json.loads(clean_id)
            tid = str(tid_dict['id'])

            df = load_data()
            # Filtra garantindo que ambos sejam strings
            row_filter = df[df['id_instalacao'].astype(str) == tid]

            if row_filter.empty:
                return [dash.no_update] * 13

            row = row_filter.iloc[0]
            itms = []
            if row['materiais_checklist']:
                for i in str(row['materiais_checklist']).split(';'):
                    if '|' in i:
                        p = i.split('|')
                        itms.append({'label': p[0], 'total': float(p[1]), 'entregue': float(p[2])})

            val_os = row.get('valor_acordado', "")

            return True, tid, row['id_instalacao'], row['descricao'], row['tecnico'], \
                str(row['data_inicio']).replace(' ', 'T'), itms, row['status'], \
                row['responsavel'], row['telefone'], row['observacoes'], val_os, ""
        except Exception as e:
            print(f"Erro ao interpretar ID de edição: {e}")
            return [dash.no_update] * 13

    # 2. Lógica para Nova O.S.
    if "btn-novo" in trig_id:
        return True, str(datetime.now().timestamp()), "", "", None, \
            datetime.now().strftime("%Y-%m-%dT%H:%M"), [], "Aberto", \
            "", "", "", "", ""

    # 3. Lógica para Fechar/Excluir/Finalizar (Fecha o modal e limpa)
    if any(x in trig_id for x in ["btn-fechar", "btn-excluir-confirmado", "btn-confirm-final-obs"]):
        return False, dash.no_update, "", "", None, "", [], "Aberto", "", "", "", "", ""

    # 4. Lógica para Salvar (se não for finalizada, fecha o modal)
    if "btn-salvar" in trig_id:
        if status_atual != "Finalizada":
            return False, dash.no_update, "", "", None, "", [], "Aberto", "", "", "", "", ""
        else:
            return [dash.no_update] * 13

    return [dash.no_update] * 13


# --- MATERIAIS, CARDS E SALVAMENTO ---
@app.callback(
    [Output('temp-items-store', 'data'), Output('input-lista', 'value')],
    [Input('btn-gerar', 'n_clicks'), Input('btn-clear-sim', 'n_clicks'), Input('btn-confirm-del-item', 'n_clicks'),
     Input({'type': 'qtd-total', 'index': ALL}, 'value'), Input({'type': 'qtd-entregue', 'index': ALL}, 'value')],
    [State('input-lista', 'value'), State('input-qtd', 'value'), State('temp-items-store', 'data'),
     State('store-index-item-deletar', 'data')],
    prevent_initial_call=True
)
def update_items(n_add, n_clr, n_del, totals, entregues, txt, q_add, current, idx_del):
    ctx = callback_context
    trig_id = ctx.triggered[0]['prop_id']
    if current:
        for i in range(min(len(current), len(totals))):
            try:
                current[i]['total'] = float(totals[i]) if totals[i] is not None else 0
                current[i]['entregue'] = float(entregues[i]) if entregues[i] is not None else 0
            except:
                pass
    if "btn-gerar" in trig_id and txt:
        current.append({'label': txt, 'total': float(q_add or 1), 'entregue': 0})
        return current, ""
    if "btn-clear-sim" in trig_id: return [], ""
    if "btn-confirm-del-item" in trig_id and idx_del is not None:
        if 0 <= idx_del < len(current): current.pop(idx_del)
        return current, dash.no_update
    return current, dash.no_update


@app.callback(Output('lista-materiais-container', 'children'), Input('temp-items-store', 'data'))
def render_list(items):
    if not items: return html.Div("Nenhum material.", className="text-muted small text-center py-2")
    rows = [dbc.Row([dbc.Col(html.Small("Item"), width=6), dbc.Col(html.Small("Total"), width=2),
                     dbc.Col(html.Small("Uso"), width=2), dbc.Col(width=2)], className="mb-2 text-info fw-bold")]
    for i, it in enumerate(items):
        cor = "#2eb82e" if it['entregue'] >= it['total'] and it['total'] > 0 else "#ffc107"
        rows.append(dbc.Row([
            dbc.Col(html.Span(it['label'], className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'qtd-total', 'index': i}, type='number', value=it['total'], size="sm"),
                    width=2),
            dbc.Col(dbc.Input(id={'type': 'qtd-entregue', 'index': i}, type='number', value=it['entregue'], size="sm",
                              style={"color": cor}), width=2),
            dbc.Col(
                dbc.Button(html.I(className="bi bi-x-circle"), id={'type': 'btn-del-single', 'index': i}, color="link",
                           className="text-danger p-0"), width=2)
        ], className="mb-2 align-items-center"))
    return rows


@app.callback(
    Output('refresh-signal', 'data', allow_duplicate=True),
    Input('salvar-manutencao-simples', 'n_clicks'),
    [State('os-manutencao', 'value'),
     State('nome-manutencao', 'value'),
     State('tel-manutencao', 'value'),
     State('tec-manutencao', 'value'),
     State('status-manutencao', 'value'),
     State('desc-manutencao', 'value'),
     State('modo-modal-agenda', 'data'),  # Aqui está o segredo (novo ou índice)
     State('tabs-agenda-cidades', 'active_tab'),
     State('refresh-signal', 'data')],
    prevent_initial_call=True
)
def salvar_ou_editar_agenda(n, os_val, nome, tel, tec, status, desc, modo, tab, sig):
    if not n: return dash.no_update

    cidade = "Divinópolis" if tab == "ag-div" else "Itaúna"
    df_agenda = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1')

    # Dados formatados
    dados_linha = {
        'id_instalacao': os_val,
        'tecnico': tec,
        'descricao': nome,
        'telefone': tel,
        'status': status,
        'observacoes': f"{desc} [{cidade}]",
        'mes_referencia': f"{datetime.now().month}/{datetime.now().year}"
    }

    if modo == "novo":
        # Adiciona nova linha
        df_nova = pd.DataFrame([dados_linha])
        df_agenda = pd.concat([df_agenda, df_nova], ignore_index=True)
    else:
        # Edita a linha existente usando o índice salvo no 'modo'
        idx = int(modo)
        for col, valor in dados_linha.items():
            df_agenda.at[idx, col] = valor

    df_agenda.to_csv(CSV_AGENDA, index=False, sep=',', encoding='latin-1')
    return (sig or 0) + 1

    # Salva no arquivo CSV da agenda
    if os.path.exists(CSV_AGENDA):
        df_agenda = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1')
        df_agenda = pd.concat([df_agenda, novo_dado], ignore_index=True)
    else:
        df_agenda = novo_dado

    df_agenda.to_csv(CSV_AGENDA, index=False, sep=',', encoding='latin-1')
    return (sig or 0) + 1


@app.callback([Output('filtro-mes', 'options'), Output('filtro-mes', 'value')], Input('refresh-signal', 'data'))
def upd_filter(n):
    df = load_data()
    mes_atual = f"{MESES_PT.get(datetime.now().strftime('%B'))}/{datetime.now().year}"
    if df.empty: return [{'label': mes_atual, 'value': mes_atual}], mes_atual
    m = sorted(df['mes_referencia'].unique().tolist(), reverse=True)
    return [{'label': i, 'value': i} for i in m], m[0]


@app.callback(
    Output('cards-area', 'children'),
    [Input('refresh-signal', 'data'), Input('filtro-mes', 'value'), Input('search-input', 'value')]
)
def render_cards(sig, mes, search):
    # ... aqui começa o código que lê o CSV de instalações ...
    df = load_data()
    if df.empty: return html.Div("Sem registros.", className="text-center w-100 mt-5 text-muted")
    df_f = df[df['mes_referencia'] == mes]
    if search:
        st = str(search).lower()
        df_f = df_f[
            (df_f['id_instalacao'].str.lower().str.contains(st)) | (df_f['descricao'].str.lower().str.contains(st)) | (
                df_f['tecnico'].str.lower().str.contains(st))]
    cards = []
    agora = datetime.now()
    for _, r in df_f.iterrows():
        t, e = 0, 0
        for i in str(r['materiais_checklist']).split(';'):
            if '|' in i: p = i.split('|'); t += float(p[1]); e += float(p[2])
        perc = int((e / t * 100)) if t > 0 else 0
        c_b = "#ff4d4d" if perc <= 30 else ("#ffcc00" if perc <= 80 else "#2eb82e")
        try:
            d_ag = datetime.strptime(str(r['data_inicio']), "%Y-%m-%d %H:%M")
        except:
            d_ag = agora
        inv = True
        if r['status'] == "Finalizada":
            c_c = "success"
        elif r['status'] == "Aberto":
            c_c = "warning";
            inv = False
        elif r['status'] == "Em Andamento":
            c_c = "primary"
        else:
            c_c = "secondary"

        # VALOR NO CARD
        valor_display = r['valor_acordado'] if 'valor_acordado' in r and r['valor_acordado'] else "0,00"

        cards.append(dbc.Col(dbc.Card([
            dbc.CardHeader([html.Small(f"Nº O.S: {r['id_instalacao']}", className="fw-bold"),
                            dbc.Badge(r['status'], color="light", text_color="dark", className="float-end")]),
            dbc.CardBody([
                html.H5(r['descricao'], className="card-title text-truncate"),
                html.P([html.I(className="bi bi-person me-2"), r['tecnico']], className="mb-1 small"),
                html.P([html.I(className="bi bi-cash-stack me-2"), html.Strong("Valor: "), f"R$ {valor_display}"],
                       className="mb-1 small text-info"),
                html.P([html.I(className="bi bi-calendar-event me-2"), d_ag.strftime('%d/%m - %H:%M')],
                       className="mb-3 small"),
                dbc.Progress(value=perc, label=f"{perc}%", animated=True, striped=True, style={"height": "18px"},
                             color=c_b)]),
            dbc.Button([html.I(className="bi bi-pencil-square me-2"), "Gerenciar"],
                       id={'type': 'edit', 'id': str(r['id_instalacao'])}, color="light", outline=True, size="sm",
                       className="m-2")
        ], color=c_c, inverse=inv, className="h-100 shadow-sm border-0 border-top border-3 border-info shadow")))
    return cards

@app.callback(
    Output("main-modal", "is_open", allow_duplicate=True), # Adicionamos o allow_duplicate
    [Input("btn-novo", "n_clicks"), # Botão Novo da Aba Principal
     Input("btn-fechar", "n_clicks"),
     Input("btn-salvar", "n_clicks")],
    [State("main-modal", "is_open")],
    prevent_initial_call=True
)
def gerenciar_modal_principal(n_novo, n_fechar, n_salvar, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open

    # Se qualquer um desses botões da Aba Principal for clicado, ele alterna o modal
    return not is_open

# --- CALLBACKS BASE ---
@app.callback(Output('visualizador-frame', 'src'), Input({'type': 'btn-ver-arquivo', 'filename': ALL}, 'n_clicks'),
              prevent_initial_call=True)
def atualizar_visualizador(n_clicks):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks): return dash.no_update
    trig_id = json.loads(ctx.triggered[0]['prop_id'].split('.n_clicks')[0])
    return f"/download/{trig_id['filename']}"


@app.callback(Output("btn-salvar-base", "children"), Input("btn-salvar-base", "n_clicks"),
              State("editor-texto", "value"), prevent_initial_call=True)
def cb_salvar_base(n, texto):
    if n:
        salvar_nota_json(texto)
        return [html.I(className="bi bi-check-all me-2"), "Salvo com Sucesso!"]
    return [html.I(className="bi bi-save me-2"), "Salvar Documentação"]


@app.callback(Output('lista-arquivos-base', 'children'), Input('upload-base', 'contents'),
              State('upload-base', 'filename'), prevent_initial_call=True)
def cb_upload_base(list_of_contents, list_of_names):
    if list_of_contents:
        for content, name in zip(list_of_contents, list_of_names):
            data = content.split(',')[1]
            with open(os.path.join(FOLDER_FILES, name), "wb") as f:
                f.write(base64.b64decode(data))
        return gerar_lista_arquivos(os.listdir(FOLDER_FILES))
    return dash.no_update


@app.callback(Output('resumo-kit-col', 'children'),
              [Input('dropdown-kit-tec', 'value'), Input('refresh-kit-signal', 'data')])
def atualizar_progresso_kit(tecnico, sig):
    if not tecnico: return ""
    df_kits = pd.read_csv(CSV_KITS, sep=',', encoding='latin-1')
    dados_tec = df_kits[df_kits['tecnico'] == tecnico]
    if dados_tec.empty: return html.Div(dbc.Badge("Sem dados salvos", color="secondary"), className="mt-4")
    total = len(dados_tec)
    ok = len(dados_tec[(dados_tec['qtd_tem'] > 0) & (dados_tec['qtd_faltante'] == 0)])
    perc = int((ok / total * 100)) if total > 0 else 0
    cor = "danger" if perc <= 30 else ("warning" if perc <= 80 else "success")
    return html.Div([html.Small(f"Integridade do Kit: {ok}/{total}", className="fw-bold text-info"),
                     dbc.Progress(value=perc, label=f"{perc}%", color=cor, striped=True, animated=True,
                                  style={"height": "20px"})], className="mt-3")


def render_aba_agenda():
    return html.Div([
        # ... abas de cidades ...
        dbc.Row([
            dbc.Col(dbc.Button([html.I(className="bi bi-plus-circle me-2"), "Nova Manutenção"],
                               id="btn-nova-agenda",  # <--- ESTE ID É A CHAVE
                               color="success"), width="auto")
        ], justify="end", className="mb-3"),
        html.Div(id="cards-agenda-area")
    ])


# Callback para abrir/fechar o modal da agenda
@app.callback(
    [Output("modal-agenda", "is_open"),
     Output("agenda-id-store", "data")],
    [Input("btn-nova-agenda", "n_clicks"),
     Input("agenda-btn-fechar", "n_clicks"),
     Input("agenda-btn-salvar", "n_clicks")],
    [State("modal-agenda", "is_open")],
    prevent_initial_call=True
)
def toggle_agenda(n_abre, n_fecha, n_salva, is_open):
    # Verifica qual botão foi clicado
    ctx = callback_context
    if not ctx.triggered:
        return is_open, dash.no_update

    trig_id = ctx.triggered[0]['prop_id']

    # Se clicou em abrir, fechar ou salvar, inverte o estado do modal (abre/fecha)
    if "btn-nova-agenda" in trig_id or "agenda-btn-fechar" in trig_id or "agenda-btn-salvar" in trig_id:
        return not is_open, str(datetime.now().timestamp())

    return is_open, dash.no_update


# Callback para mostrar a caixa de encerramento apenas quando for "Resolvido"
@app.callback(
    Output("div-info-final", "style"),
    Input("agenda-status", "value")
)
def mostrar_obs_final(status):
    if status == "Resolvido":
        return {"display": "block"}
    return {"display": "none"}


# Callback para SALVAR os dados da Agenda
@app.callback(
    Output("refresh-signal", "data", allow_duplicate=True),
    Input("agenda-btn-salvar", "n_clicks"),
    [State("agenda-id-manual", "value"), State("agenda-cliente", "value"),
     State("agenda-tel", "value"), State("agenda-tec", "value"),
     State("agenda-status", "value"), State("agenda-data", "value"),
     State("agenda-obs", "value"), State("agenda-info-final", "value"),
     State("tabs-agenda-cidades", "active_tab"), State("refresh-signal", "data")],
    prevent_initial_call=True
)
def salvar_dados_agenda(n, os_id, cliente, tel, tec, status, data, obs, info_f, tab, sig):
    if not n: return dash.no_update

    cidade = "Divinópolis" if tab == "ag-div" else "Itaúna"
    df = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1')

    # Combinamos o problema com a info de encerramento se houver
    obs_completa = f"PROBLEMA: {obs}"
    if info_f: obs_completa += f" | ENCERRAMENTO: {info_f}"

    # Adicionamos a tag da cidade nas observações para o filtro funcionar
    obs_completa += f" [{cidade}]"

    nova_linha = {
        'id_instalacao': os_id if os_id else "SN",
        'tecnico': tec, 'descricao': cliente, 'status': status,
        'telefone': tel, 'observacoes': obs_completa, 'data_inicio': data,
        'mes_referencia': f"{MESES_PT.get(datetime.now().strftime('%B'))}/{datetime.now().year}"
    }

    df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
    df.to_csv(CSV_AGENDA, index=False, sep=',', encoding='latin-1')
    return (sig or 0) + 1


@app.callback(
    Output("cards-agenda-area", "children"),
    [Input("refresh-signal", "data"),
     Input("tabs-agenda-cidades", "active_tab")]
)
def render_agenda_cards_grandes(sig, tab):
    if not os.path.exists(CSV_AGENDA):
        return html.Div("Nenhum agendamento encontrado.", className="text-center mt-5 text-muted")

    df = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1')
    cidade_alvo = "Divinópolis" if tab == "ag-div" else "Itaúna"
    df_cidade = df[df['observacoes'].str.contains(cidade_alvo, case=False, na=False)]

    if df_cidade.empty:
        return html.Div(f"Nenhum serviço agendado para {cidade_alvo}.", className="text-center w-100 mt-5 text-muted")

    tecnicos_no_arquivo = df_cidade['tecnico'].unique()
    colunas_tecnicos = []

    for tec in tecnicos_no_arquivo:
        if not tec or str(tec).strip() == "" or str(tec).lower() == "nan":
            continue

        df_tec = df_cidade[df_cidade['tecnico'] == tec]
        cards_do_tecnico = []

        for _, r in df_tec.iterrows():
            # Construção do Card
            card = dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Span(f"O.S: {r['id_instalacao']}", className="badge bg-info text-dark fw-bold"),
                        dbc.Button(html.I(className="bi bi-pencil-square"),
                                   id={'type': 'btn-editar-agenda', 'index': str(r.name)},
                                   size="sm", color="warning", outline=True)
                    ], className="d-flex justify-content-between align-items-center mb-3"),

                    html.H5(r['descricao'], className="fw-bold mb-1", style={"color": "#fff"}),
                    html.P(r['telefone'], className="text-muted small mb-3"),

                    html.Div([
                        html.Small("OBSERVAÇÕES:", className="text-info fw-bold d-block", style={"fontSize": "10px"}),
                        html.P(str(r['observacoes']).split('[')[0],
                               style={"fontSize": "13px", "color": "#ddd", "backgroundColor": "#1a1a1a",
                                      "padding": "8px", "borderRadius": "5px"})
                    ], className="mb-2"),

                    dbc.Badge(r['status'],
                              color="success" if r['status'] == "Finalizada" else "warning" if r[
                                                                                                   'status'] == "Pendência" else "primary",
                              className="w-100")
                ], className="p-3")
            ], className="mb-4 shadow-lg border-0", style={"backgroundColor": "#323232", "borderRadius": "12px"})

            cards_do_tecnico.append(card)

        # Montagem da Coluna
        coluna = dbc.Col([
            html.Div([
                html.H4([html.I(className="bi bi-person-workspace me-2"), tec.upper()],
                        className="text-center p-3 text-white fw-bold rounded-top mb-0",
                        style={"backgroundColor": "#0d6efd", "fontSize": "18px"}),
                html.Div(cards_do_tecnico, className="p-3", style={"backgroundColor": "#212529"})
            ], className="h-100 shadow-sm")
        ], width=12, md=10, lg=10)

        colunas_tecnicos.append(coluna)

    return dbc.Row(colunas_tecnicos, className="g-4")  # <--- AQUI TERMINA A FUNÇÃO


@app.callback(
    [Output("modal-simples-id", "is_open"),
     Output("os-manutencao", "value"),
     Output("nome-manutencao", "value"),
     Output("tel-manutencao", "value"),
     Output("tec-manutencao", "value"),
     Output("status-manutencao", "value"),
     Output("desc-manutencao", "value"),
     Output("modo-modal-agenda", "data")],
    [Input("btn-nova-agenda", "n_clicks"),  # <--- CORRIGIDO PARA O SEU ID REAL
     Input({'type': 'btn-editar-agenda', 'index': ALL}, 'n_clicks'),
     Input("fechar-manutencao-simples", "n_clicks"),
     Input("salvar-manutencao-simples", "n_clicks")],
    [State("modal-simples-id", "is_open")],
    prevent_initial_call=True
)
def gerenciar_modal_manutencao(n_novo, n_editar, n_fechar, n_salvar, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, "novo"

    trig_id = ctx.triggered[0]['prop_id']

    # Se clicou em Nova Manutenção (usando o ID btn-nova-agenda)
    if "btn-nova-agenda" in trig_id:
        return True, "", "", "", None, "Aberto", "", "novo"

    # Se clicou no lápis de editar manutenção
    if "btn-editar-agenda" in trig_id:
        import json
        idx = json.loads(trig_id.split('.')[0])['index']
        df = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1')
        linha = df.loc[int(idx)]
        return True, linha['id_instalacao'], linha['descricao'], linha['telefone'], linha['tecnico'], linha['status'], str(linha['observacoes']).split('[')[0], idx

    # Se salvou ou fechou
    return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, "novo"

# INICIALIZAÇÃO DO SERVIDOR (Apenas uma vez no final do arquivo)
if __name__ == '__main__':
    app.run(debug=True, port=8050)