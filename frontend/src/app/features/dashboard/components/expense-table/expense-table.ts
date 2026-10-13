
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import {
  AnalyticsService,
  Empenho,
} from '../../../../core/services/analytics.service';

@Component({
  selector: 'app-expense-table',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './expense-table.html',
  styleUrl: './expense-table.scss',
})
export class ExpenseTable implements OnInit {
  private readonly analytics = inject(AnalyticsService);

  empenhos = signal<Empenho[]>([]);
  carregando = signal(true);
  erro = signal(false);

  ngOnInit(): void {
    this.carregarEmpenhos();
  }

  carregarEmpenhos(): void {
    this.carregando.set(true);
    this.erro.set(false);

    this.analytics
      .getMaioresEmpenhos(20)
      .pipe(finalize(() => this.carregando.set(false)))
      .subscribe({
        next: (dados) => {
          this.empenhos.set(dados);
        },
        error: (error) => {
          console.error('Erro ao carregar empenhos:', error);
          this.erro.set(true);
        },
      });
  }
}
