
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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

@Injectable({
  providedIn: 'root',
})

export class AnalyticsService {
  private readonly http = inject(HttpClient);

  private readonly apiUrl = 'http://localhost:8000/api/analytics';

  getResumo(): Observable<ResumoFinanceiro> {
    return this.http.get<ResumoFinanceiro>(
      `${this.apiUrl}/resumo`
    );
  }

  getOrgaos(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(
      `${this.apiUrl}/orgaos`
    );
  }

  getUnidades(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(
      `${this.apiUrl}/unidades`
    );
  }

  getEvolucaoMensal(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(
      `${this.apiUrl}/evolucao-mensal`
    );
  }

  getSituacaoPagamento(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(
      `${this.apiUrl}/situacao-pagamento`
    );
  }

  getAnomalias(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(
      `${this.apiUrl}/anomalias`
    );
  }
}
