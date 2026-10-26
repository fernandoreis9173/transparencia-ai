
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ResumoFinanceiro {
  quantidade_empenhos: number;
  quantidade_exercicios: number;
  total_empenhado: number;
  total_liquidado: number;
  total_pago: number;
  total_pago_restos_a_pagar: number;
  quantidade_nao_pago: number;
  quantidade_pagamento_parcial: number;
  quantidade_pago: number;
  quantidade_anomalias: number;
}

export interface Empenho {
  ano_exercicio: number;
  num_empenho: string;
  data_registro_empenho: string;
  nome_orgao: string;
  nome_uo: string;
  nome_favorecido: string;
  vl_empenhado: number;
  vl_liquidado: number;
  vl_pago: number;
  liquidado_maior_que_empenhado: boolean;
}

export interface FiltrosAnalytics {
  ano_exercicio?: number | null;
  cod_uo?: string | null;
  nome_favorecido?: string | null;
  situacao_pagamento?: 'NAO_PAGO' | 'PAGAMENTO_PARCIAL' | 'PAGO' | null;
  apenas_anomalias?: boolean | null;
}

@Injectable({
  providedIn: 'root',
})

export class AnalyticsService {
  private readonly http = inject(HttpClient);

  private readonly apiUrl = 'http://localhost:8000/api/analytics';

  private montarParametros(filtros: FiltrosAnalytics = {}): HttpParams {
  let params = new HttpParams();

  if (filtros.ano_exercicio != null) {
    params = params.set('ano_exercicio', filtros.ano_exercicio);
  }

  if (filtros.cod_uo?.trim()) {
    params = params.set('cod_uo', filtros.cod_uo.trim());
  }

  if (filtros.nome_favorecido?.trim()) {
    params = params.set('nome_favorecido', filtros.nome_favorecido.trim());
  }

  if (filtros.situacao_pagamento) {
    params = params.set('situacao_pagamento', filtros.situacao_pagamento);
  }

  if (filtros.apenas_anomalias != null) {
    params = params.set('apenas_anomalias', filtros.apenas_anomalias);
  }

  return params;
}

  getResumo(filtros: FiltrosAnalytics = {}): Observable<ResumoFinanceiro> {
  return this.http.get<ResumoFinanceiro>(
    `${this.apiUrl}/resumo`,
    { params: this.montarParametros(filtros) }
  );
}

getOrgaos(filtros: FiltrosAnalytics = {}): Observable<Record<string, unknown>[]> {
  return this.http.get<Record<string, unknown>[]>(
    `${this.apiUrl}/orgaos`,
    { params: this.montarParametros(filtros) }
  );
}

getUnidades(filtros: FiltrosAnalytics = {}): Observable<Record<string, unknown>[]> {
  return this.http.get<Record<string, unknown>[]>(
    `${this.apiUrl}/unidades`,
    { params: this.montarParametros(filtros) }
  );
}

getEvolucaoMensal(filtros: FiltrosAnalytics = {}): Observable<Record<string, unknown>[]> {
  return this.http.get<Record<string, unknown>[]>(
    `${this.apiUrl}/evolucao-mensal`,
    { params: this.montarParametros(filtros) }
  );
}

getSituacaoPagamento(filtros: FiltrosAnalytics = {}): Observable<Record<string, unknown>[]> {
  return this.http.get<Record<string, unknown>[]>(
    `${this.apiUrl}/situacao-pagamento`,
    { params: this.montarParametros(filtros) }
  );
}

getAnomalias(filtros: FiltrosAnalytics = {}): Observable<Record<string, unknown>[]> {
  return this.http.get<Record<string, unknown>[]>(
    `${this.apiUrl}/anomalias`,
    { params: this.montarParametros(filtros) }
  );
}

getMaioresEmpenhos(
  limite = 20,
  filtros: FiltrosAnalytics = {}
): Observable<Empenho[]> {
  const params = this.montarParametros(filtros).set('limite', limite);

  return this.http.get<Empenho[]>(
    `${this.apiUrl}/maiores-empenhos`,
    { params }
  );
}
}
