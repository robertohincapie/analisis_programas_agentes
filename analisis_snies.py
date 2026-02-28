from langgraph.graph import StateGraph, START, END
import json
from estado import AgentState
from estado import Nivel
from agentes_de_analisis import nodo_analizar_num_programas_instituciones
from agentes_de_analisis import nodo_analizar_matriculas_vs_estudiantes
from agentes_de_analisis import nodo_analizar_matriculas_vs_tiempo
from agentes_de_analisis import nodo_analizar_programas_por_departamento_municipio
from agentes_de_analisis import nodo_analizar_num_estudiantes_tiempo
#from buscador_programas import build_query_agent
from creador_reporte import nodo_creador_reporte

from lector import nodo_lector_snies  # importa tu tool
builder = StateGraph(AgentState)
builder.add_node("lector_snies", nodo_lector_snies)
builder.add_node("analizar_num_programas_instituciones", nodo_analizar_num_programas_instituciones)
builder.add_node("analizar_matriculas_vs_estudiantes", nodo_analizar_matriculas_vs_estudiantes)
builder.add_node("analizar_matriculas_vs_tiempo", nodo_analizar_matriculas_vs_tiempo)
builder.add_node("analizar_programas_por_departamento_municipio", nodo_analizar_programas_por_departamento_municipio)
builder.add_node("analizar_num_estudiantes_tiempo", nodo_analizar_num_estudiantes_tiempo)
builder.add_node("creador_reporte", nodo_creador_reporte)
builder.add_edge(START, "lector_snies")
builder.add_edge("lector_snies", "analizar_num_programas_instituciones")
builder.add_edge("analizar_num_programas_instituciones", "analizar_matriculas_vs_estudiantes")
builder.add_edge("analizar_matriculas_vs_estudiantes", "analizar_matriculas_vs_tiempo")
builder.add_edge("analizar_matriculas_vs_tiempo", "analizar_programas_por_departamento_municipio")
builder.add_edge("analizar_programas_por_departamento_municipio", "analizar_num_estudiantes_tiempo")
builder.add_edge("analizar_num_estudiantes_tiempo", "creador_reporte")
builder.add_edge("creador_reporte", END)

graph = builder.compile()