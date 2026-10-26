import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface FiltrosChat {
  ano_exercicio?: number | null;
  cod_uo?: string | null;
  nome_favorecido?: string | null;
  situacao_pagamento?:
    | 'NAO_PAGO'
    | 'PAGAMENTO_PARCIAL'
    | 'PAGO'
    | null;
  apenas_anomalias?: boolean | null;
}

export interface PerguntaChatRequest {
  pergunta: string;
  filtros?: FiltrosChat;
}

export interface PerguntaChatResponse {
  resposta: string;
  provedor: string;
  intencao: string;
  quantidade_resultados: number;
  total_pendentes?: number | null;
  dados: Record<string, unknown>[];
  aviso: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly http = inject(HttpClient);

  private readonly apiUrl = 'http://localhost:8000/api/chat';

  perguntar(
    pergunta: string,
    filtros: FiltrosChat = {}
  ): Observable<PerguntaChatResponse> {
    const payload: PerguntaChatRequest = {
      pergunta: pergunta.trim(),
      filtros
    };

    return this.http.post<PerguntaChatResponse>(
      `${this.apiUrl}/perguntar`,
      payload
    );
  }
}
