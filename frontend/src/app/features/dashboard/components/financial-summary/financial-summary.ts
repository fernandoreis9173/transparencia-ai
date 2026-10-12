
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { AnalyticsService, ResumoFinanceiro } from '../../../../core/services/analytics.service';

@Component({
  selector: 'app-financial-summary',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './financial-summary.html',
  styleUrl: './financial-summary.scss',
})
export class FinancialSummary implements OnInit {
  private readonly analyticsService = inject(AnalyticsService);

  resumo = signal<ResumoFinanceiro | null>(null);
  carregando = signal(true);
  erro = signal(false);

  ngOnInit(): void {
    this.carregarResumo();
  }

  carregarResumo(): void {
    this.carregando.set(true);
    this.erro.set(false);

    this.analyticsService.getResumo().subscribe({
      next: (dados) => {
        this.resumo.set(dados);
        this.carregando.set(false);
      },
      error: (error) => {
        console.error('[Cards] Falha ao buscar resumo:', error);
        this.erro.set(true);
        this.carregando.set(false);
      },
    });
  }

  tentarNovamente(): void {
    this.carregarResumo();
  }
}
