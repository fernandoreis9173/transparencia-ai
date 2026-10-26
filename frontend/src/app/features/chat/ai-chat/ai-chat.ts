import { Component, Input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  ChatService,
  FiltrosChat,
  PerguntaChatResponse,
} from '../../../core/services/chat.service';

interface MensagemChat {
  pergunta: string;
  resposta?: string;
  provedor?: string;
  aviso?: string;
  erro?: string;
  carregando: boolean;
  intencao?: string;
  dados?: Record<string, unknown>[];
  quantidadeResultados?: number;
  totalPendentes?: number | null;
}

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [FormsModule],
  styleUrl: './ai-chat.scss',
  templateUrl: './ai-chat.html',
})

export class AiChat {
  @Input() filtros: FiltrosChat = {};

  pergunta = '';
  mensagens = signal<MensagemChat[]>([]);
  carregando = signal(false);
  erroGeral = signal('');

  constructor(private readonly chatService: ChatService) {}

  enviarPergunta(): void {
    const perguntaAtual = this.pergunta.trim();

    if (!perguntaAtual || this.carregando()) {
      return;
    }

    this.erroGeral.set('');
    this.pergunta = '';
    this.carregando.set(true);

    this.mensagens.update((lista) => [
      ...lista,
      { pergunta: perguntaAtual, carregando: true },
    ]);

    const indice = this.mensagens().length - 1;

    const atualizar = (parcial: Partial<MensagemChat>) =>
      this.mensagens.update((lista) =>
        lista.map((mensagem, i) =>
          i === indice ? { ...mensagem, ...parcial } : mensagem,
        ),
      );

    this.chatService.perguntar(perguntaAtual, this.filtros).subscribe({
      next: (resultado: PerguntaChatResponse) => {
        atualizar({
          resposta: this.formatarResposta(resultado.resposta),
          provedor: resultado.provedor,
          aviso: resultado.aviso,
          dados: resultado.dados ?? [],
          intencao: resultado.intencao,
          quantidadeResultados: resultado.quantidade_resultados,
          totalPendentes: resultado.total_pendentes,
          carregando: false,
        });

        this.carregando.set(false);
      },
      error: (erro) => {
        atualizar({
          carregando: false,
          erro:
            erro?.error?.detail ??
            'Não foi possível consultar o assistente. Verifique se a API está disponível.',
        });

        this.carregando.set(false);
      },
    });
  }

  private formatarResposta(valor: unknown): string {
    if (typeof valor === 'string') {
      return valor;
    }

    if (valor == null) {
      return '';
    }

    if (Array.isArray(valor)) {
      return valor.map((item) => this.formatarResposta(item)).join('\n\n');
    }

    if (typeof valor === 'object' && 'resposta' in valor) {
      return this.formatarResposta(
        (valor as { resposta: unknown }).resposta,
      );
    }

    return JSON.stringify(valor, null, 2);
  }

  /**
   * Só apresenta a tabela quando os dados contêm registros individuais
   * de empenhos, evitando tabelas inadequadas para respostas agregadas.
   */
  temTabelaEmpenhos(mensagem: MensagemChat): boolean {
    return Boolean(
      mensagem.dados?.length &&
      mensagem.dados.some((item) => item['num_empenho'] != null),
    );
  }

  /**
   * Para consultas com tabela, troca a resposta longa da IA por um resumo
   * curto, evitando listar os mesmos empenhos duas vezes.
   */
  respostaExibida(mensagem: MensagemChat): string {
    if (!this.temTabelaEmpenhos(mensagem)) {
      return mensagem.resposta ?? '';
    }

    const intencao = mensagem.intencao;
    const quantidade = mensagem.dados?.filter(
      (item) => item['num_empenho'] != null,
    ).length ?? 0;

    if (intencao === 'situacao_pagamento') {
      const total = mensagem.totalPendentes;

      if (total != null) {
        return `A consulta identificou ${total} empenhos pendentes. A tabela abaixo apresenta ${quantidade} registro(s) retornado(s) pela consulta.`;
      }

      return `A consulta retornou ${quantidade} registro(s) de empenhos para análise. Confira os detalhes na tabela abaixo.`;
    }

    if (intencao === 'maiores_empenhos') {
      return `Estes são os ${quantidade} maiores empenhos retornados pela consulta, ordenados pelo valor empenhado.`;
    }

    if (intencao === 'anomalias') {
      return `A consulta retornou ${quantidade} registro(s) sinalizado(s) para análise. A diferença entre liquidado e empenhado é um indicador para investigação, não uma comprovação de irregularidade.`;
    }

    return mensagem.resposta ?? '';
  }

  formatarMoeda(valor: unknown): string {
    const numero = Number(valor ?? 0);

    if (!Number.isFinite(numero)) {
      return '—';
    }

    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(numero);
  }

  formatarDiferenca(item: Record<string, unknown>): string {
    const empenhado = Number(item['vl_empenhado'] ?? 0);
    const liquidado = Number(item['vl_liquidado'] ?? 0);

    return this.formatarMoeda(liquidado - empenhado);
  }

  nomeProvedor(provedor?: string): string {
    const nomes: Record<string, string> = {
      gemini: 'Gemini',
      openai: 'GPT (OpenAI)',
      ollama: 'Ollama',
      postgresql_fallback: 'Resposta local do PostgreSQL',
    };

    return provedor
      ? nomes[provedor] ?? provedor
      : 'Provedor não informado';
  }

  rastrearMensagem(index: number, mensagem: MensagemChat): string {
    return `${index}-${mensagem.pergunta}`;
  }
}
