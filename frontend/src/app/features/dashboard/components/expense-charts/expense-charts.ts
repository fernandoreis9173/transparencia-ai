import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, OnInit, SimpleChanges, inject, signal } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { forkJoin } from 'rxjs';
import { AnalyticsService, FiltrosAnalytics } from '../../../../core/services/analytics.service';

type Row = Record<string, unknown>;

@Component({
  selector: 'app-expense-charts',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './expense-charts.html',
  styleUrl: './expense-charts.scss',
})
export class ExpenseCharts implements OnInit, OnChanges {
  private readonly analytics = inject(AnalyticsService);

  carregando = signal(true);
  erro = signal(false);
  semDadosMensais = signal(false);

  barData = signal<ChartData<'bar'>>({ labels: [], datasets: [] });
  lineData = signal<ChartData<'line'>>({ labels: [], datasets: [] });
  doughnutData = signal<ChartData<'doughnut'>>({ labels: [], datasets: [] });

  readonly barOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: true },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value) =>
            new Intl.NumberFormat('pt-BR', {
              notation: 'compact',
              maximumFractionDigits: 1,
            }).format(Number(value)),
        },
      },
    },
  };

  readonly lineOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index',
    },
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value) =>
            new Intl.NumberFormat('pt-BR', {
              notation: 'compact',
              maximumFractionDigits: 1,
            }).format(Number(value)),
        },
      },
    },
  };

  readonly doughnutOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
  };

  @Input() filtros: FiltrosAnalytics = {};

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['filtros'] && !changes['filtros'].firstChange) {
      this.carregarGraficos();
    }
  }

  ngOnInit(): void {
    this.carregarGraficos();
  }

  carregarGraficos(): void {
    this.carregando.set(true);
    this.erro.set(false);

    forkJoin({
      unidades: this.analytics.getUnidades(this.filtros),
      mensal: this.analytics.getEvolucaoMensal(this.filtros),
      pagamentos: this.analytics.getSituacaoPagamento(this.filtros),
    }).subscribe({
      next: (resposta) => {
        const unidades = this.extrairLinhas(resposta.unidades);
        const mensal = this.extrairLinhas(resposta.mensal);
        const pagamentos = this.extrairLinhas(resposta.pagamentos);

        this.montarBarras(unidades);
        this.montarLinha(mensal);
        this.montarRosca(pagamentos);

        this.semDadosMensais.set(this.lineData().labels?.length === 0);
        this.carregando.set(false);
      },
      error: (error) => {
        console.error('[Gráficos] Erro ao consultar a API:', error);
        this.erro.set(true);
        this.carregando.set(false);
      },
    });
  }

  tentarNovamente(): void {
    this.carregarGraficos();
  }

  private extrairLinhas(valor: unknown): Row[] {
    if (Array.isArray(valor)) {
      return valor.filter((item): item is Row => item !== null && typeof item === 'object');
    }

    if (valor && typeof valor === 'object') {
      const objeto = valor as Record<string, unknown>;

      for (const chave of ['dados', 'data', 'items', 'resultados', 'results']) {
        if (Array.isArray(objeto[chave])) {
          return this.extrairLinhas(objeto[chave]);
        }
      }
    }

    return [];
  }

  private encontrarCampo(linha: Row, candidatos: string[], tipo: 'texto' | 'numero'): unknown {
    const entradas = Object.entries(linha);

    for (const candidato of candidatos) {
      const entrada = entradas.find(
        ([chave, valor]) =>
          chave.toLowerCase() === candidato.toLowerCase() && this.tipoValido(valor, tipo),
      );

      if (entrada) return entrada[1];
    }

    const palavras =
      tipo === 'numero'
        ? ['total_empenhado', 'vl_empenhado', 'valor', 'quantidade', 'total', 'pago', 'liquidado']
        : ['unidade', 'nome', 'mes', 'mês', 'periodo', 'período', 'situacao', 'situação', 'status'];

    const entrada = entradas.find(
      ([chave, valor]) =>
        palavras.some((palavra) => chave.toLowerCase().includes(palavra)) &&
        this.tipoValido(valor, tipo),
    );

    if (entrada) return entrada[1];

    if (tipo === 'numero') {
      return entradas.find(([, valor]) => this.tipoValido(valor, tipo))?.[1];
    }

    return entradas.find(([, valor]) => this.tipoValido(valor, tipo))?.[1];
  }

  private tipoValido(valor: unknown, tipo: 'texto' | 'numero'): boolean {
    if (tipo === 'numero') {
      return valor !== null && valor !== '' && Number.isFinite(Number(valor));
    }

    return typeof valor === 'string' && valor.trim().length > 0;
  }

  private numero(valor: unknown): number {
    const resultado = Number(valor);
    return Number.isFinite(resultado) ? resultado : 0;
  }

  private montarBarras(linhas: Row[]): void {
    const dados = linhas
      .map((linha) => ({
        nome: String(linha['nome_uo'] ?? 'Unidade sem nome'),
        valor: this.numero(linha['total_empenhado']),
      }))
      .sort((a, b) => b.valor - a.valor)
      .slice(0, 8);

    this.barData.set({
      labels: dados.map((item) => item.nome),
      datasets: [
        {
          data: dados.map((item) => item.valor),
          label: 'Total empenhado (R$)',
          backgroundColor: '#2563eb',
          borderRadius: 5,
        },
      ],
    });
  }

  private montarLinha(linhas: Row[]): void {
    const dados = linhas
      .map((linha) => {
        const mes = String(linha['mes'] ?? '');
        const [ano, numeroMes] = mes.split('-').map(Number);

        const nomeMes =
          ano && numeroMes
            ? new Date(ano, numeroMes - 1, 1).toLocaleDateString('pt-BR', {
                month: 'short',
                year: '2-digit',
              })
            : mes;

        return {
          mes: nomeMes,
          data: mes,
          empenhado: this.numero(linha['total_empenhado']),
          liquidado: this.numero(linha['total_liquidado']),
          pago: this.numero(linha['total_pago']),
        };
      })
      .filter((item) => /^\d{4}-\d{2}-\d{2}$/.test(item.data))
      .sort((a, b) => a.data.localeCompare(b.data));

    this.lineData.set({
      labels: dados.map((item) => item.mes),
      datasets: [
        {
          data: dados.map((item) => item.empenhado),
          label: 'Empenhado',
          borderColor: '#2563eb',
          backgroundColor: '#2563eb',
          tension: 0.3,
        },
        {
          data: dados.map((item) => item.liquidado),
          label: 'Liquidado',
          borderColor: '#f59e0b',
          backgroundColor: '#f59e0b',
          tension: 0.3,
        },
        {
          data: dados.map((item) => item.pago),
          label: 'Pago',
          borderColor: '#16a34a',
          backgroundColor: '#16a34a',
          tension: 0.3,
        },
      ],
    });
  }

  private montarRosca(linhas: Row[]): void {
    const nomes: Record<string, string> = {
      NAO_PAGO: 'Não pago',
      PAGO: 'Pago',
      PAGAMENTO_PARCIAL: 'Pagamento parcial',
    };

    const dados = linhas.map((linha) => {
      const situacao = String(linha['situacao_pagamento'] ?? 'NAO_INFORMADO');

      return {
        nome: nomes[situacao] ?? situacao,
        quantidade: this.numero(linha['quantidade_empenhos']),
      };
    });

    this.doughnutData.set({
      labels: dados.map((item) => item.nome),
      datasets: [
        {
          data: dados.map((item) => item.quantidade),
          label: 'Quantidade de empenhos',
          backgroundColor: ['#f59e0b', '#16a36a', '#8b5cf6'],
          borderWidth: 2,
          borderColor: '#ffffff',
        },
      ],
    });
  }
}
