
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
        lista.map((m, i) => (i === indice ? { ...m, ...parcial } : m)),
      );

    this.chatService
      .perguntar(perguntaAtual, this.filtros)
      .subscribe({
        next: (resultado: PerguntaChatResponse) => {
          const resposta: unknown = resultado.resposta;
          atualizar({
            resposta: Array.isArray(resposta)
              ? resposta.join('\n\n')
              : String(resposta ?? ''),
            provedor: resultado.provedor,
            aviso: resultado.aviso,
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

  rastrearMensagem(
    index: number,
    mensagem: MensagemChat,
  ): string {
    return `${index}-${mensagem.pergunta}`;
  }
}
