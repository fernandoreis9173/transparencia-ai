
import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, OnInit, SimpleChanges, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import {
  AnalyticsService,
  Empenho,
  FiltrosAnalytics,
} from '../../../../core/services/analytics.service';

@Component({
  selector: 'app-expense-table',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './expense-table.html',
  styleUrl: './expense-table.scss',
})
export class ExpenseTable implements OnInit, OnChanges {
  private readonly analytics = inject(AnalyticsService);

  empenhos = signal<Empenho[]>([]);
  carregando = signal(true);
  erro = signal(false);

  @Input() filtros: FiltrosAnalytics = {};

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['filtros'] && !changes['filtros'].firstChange) {
      this.carregarEmpenhos();
    }
  }

  ngOnInit(): void {
    this.carregarEmpenhos();
  }

  carregarEmpenhos(): void {
    this.carregando.set(true);
    this.erro.set(false);

    this.analytics
      .getMaioresEmpenhos(20, this.filtros)
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
