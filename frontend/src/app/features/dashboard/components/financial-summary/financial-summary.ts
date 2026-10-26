
import { CommonModule } from '@angular/common';
import {
  Component,
  Input,
  OnChanges,
  OnInit,
  SimpleChanges,
  inject,
  signal,
} from '@angular/core';
import { finalize, Subscription } from 'rxjs';

import { AnalyticsService, FiltrosAnalytics, ResumoFinanceiro } from '../../../../core/services/analytics.service';

@Component({
  selector: 'app-financial-summary',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './financial-summary.html',
  styleUrl: './financial-summary.scss',
})
export class FinancialSummary implements OnInit, OnChanges {
  private readonly analyticsService = inject(AnalyticsService);
  private requisicao?: Subscription;
  private inicializado = false;

  @Input() filtros: FiltrosAnalytics = {};

  resumo = signal<ResumoFinanceiro | null>(null);
  carregando = signal(true);
  erro = signal(false);

  ngOnInit(): void {
    this.inicializado = true;
    this.carregarResumo();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.inicializado && changes['filtros']) {
      this.carregarResumo();
    }
  }

  carregarResumo(): void {
    this.requisicao?.unsubscribe();

    this.carregando.set(true);
    this.erro.set(false);

    this.requisicao = this.analyticsService
      .getResumo(this.filtros)
      .pipe(
        finalize(() => this.carregando.set(false)),
      )
      .subscribe({
        next: (dados) => {
          this.resumo.set(dados);
        },
        error: (error) => {
          console.error('[Cards] Falha ao buscar resumo:', error);
          this.erro.set(true);
        },
      });
  }

  tentarNovamente(): void {
    this.carregarResumo();
  }
}
