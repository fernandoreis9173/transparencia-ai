
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import {
  ChartData,
  ChartOptions,
} from 'chart.js';
import { forkJoin } from 'rxjs';
import { AnalyticsService } from '../../../../core/services/analytics.service';

type Row = Record<string, unknown>;

@Component({
  selector: 'app-expense-charts',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './expense-charts.html',
  styleUrl: './expense-charts.scss',
})
export class ExpenseCharts implements OnInit {
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
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } },
  };

  readonly doughnutOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
  };

  ngOnInit(): void {
    this.carregarGraficos();
  }

  carregarGraficos(): void {
    this.carregando.set(true);
    this.erro.set(false);

    forkJoin({
      unidades: this.analytics.getUnidades(),
      mensal: this.analytics.getEvolucaoMensal(),
      pagamentos: this.analytics.getSituacaoPagamento(),
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
      return valor.filter(
        (item): item is Row =>
          item !== null && typeof item === 'object',
      );
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

  private encontrarCampo(
    linha: Row,
    candidatos: string[],
    tipo: 'texto' | 'numero',
  ): unknown {
    const entradas = Object.entries(linha);

    for (const candidato of candidatos) {
      const entrada = entradas.find(
        ([chave, valor]) =>
          chave.toLowerCase() === candidato.toLowerCase() &&
          this.tipoValido(valor, tipo),
      );

      if (entrada) return entrada[1];
    }

    const palavras = tipo === 'numero'
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
      return valor !== null && valor !== '' &&
        Number.isFinite(Number(valor));
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
        nome: String(
          this.encontrarCampo(
            linha,
            ['nome_unidade', 'unidade_orcamentaria', 'unidade', 'nome', 'descricao'],
            'texto',
          ) ?? 'Unidade sem nome',
        ),
        valor: this.numero(
          this.encontrarCampo(
            linha,
            ['total_empenhado', 'vl_empenhado', 'valor_empenhado', 'valor', 'total'],
            'numero',
          ),
        ),
      }))
      .filter((item) => item.valor >= 0)
      .sort((a, b) => b.valor - a.valor)
      .slice(0, 8);

    this.barData.set({
      labels: dados.map((item) => item.nome),
      datasets: [{
        data: dados.map((item) => item.valor),
        label: 'Valor empenhado (R$)',
        backgroundColor: '#2563eb',
        borderRadius: 5,
      }],
    });
  }

  private montarLinha(linhas: Row[]): void {
    const dados = linhas.map((linha) => ({
      nome: String(
        this.encontrarCampo(
          linha,
          ['mes', 'mês', 'mes_referencia', 'periodo', 'referencia', 'ano_mes'],
          'texto',
        ) ?? '',
      ),
      valor: this.numero(
        this.encontrarCampo(
          linha,
          ['total_empenhado', 'vl_empenhado', 'valor_empenhado', 'valor', 'total'],
          'numero',
        ),
      ),
    })).filter((item) => item.nome !== '');

    this.lineData.set({
      labels: dados.map((item) => item.nome),
      datasets: [{
        data: dados.map((item) => item.valor),
        label: 'Despesas (R$)',
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.12)',
        pointBackgroundColor: '#2563eb',
        fill: true,
        tension: 0.3,
      }],
    });
  }

  private montarRosca(linhas: Row[]): void {
    const dados = linhas.map((linha) => ({
      nome: String(
        this.encontrarCampo(
          linha,
          ['situacao', 'situação', 'status', 'descricao', 'nome'],
          'texto',
        ) ?? 'Não informado',
      ),
      valor: this.numero(
        this.encontrarCampo(
          linha,
          ['quantidade', 'total', 'quantidade_empenhos', 'valor', 'total_pago'],
          'numero',
        ),
      ),
    }));

    this.doughnutData.set({
      labels: dados.map((item) => item.nome),
      datasets: [{
        data: dados.map((item) => item.valor),
        backgroundColor: ['#2563eb', '#16a36a', '#f59e0b', '#8b5cf6', '#ef4444'],
        borderWidth: 2,
        borderColor: '#ffffff',
      }],
    });
  }
}
