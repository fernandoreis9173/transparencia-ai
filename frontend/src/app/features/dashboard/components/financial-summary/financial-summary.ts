
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
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

  resumo: ResumoFinanceiro | null = null;
  carregando = true;
  erro = false;

  ngOnInit(): void {
    console.log('[Cards] Componente inicializado');
    this.carregarResumo();
  }

  carregarResumo(): void {
    this.carregando = true;
    this.erro = false;

    this.analyticsService.getResumo().subscribe({
      next: (dados) => {
        console.log('[Cards] Dados recebidos:', dados);
        this.resumo = dados;
        this.carregando = false;

        console.log('[Cards] Estado final:', {
          carregando: this.carregando,
          erro: this.erro,
          resumo: this.resumo,
        });
      },
      error: (error) => {
        console.error('[Cards] Falha ao buscar resumo:', error);
        this.erro = true;
        this.carregando = false;
      },
    });
  }

  tentarNovamente(): void {
    this.carregarResumo();
  }
}
