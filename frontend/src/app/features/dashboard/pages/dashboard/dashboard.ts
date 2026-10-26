
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FinancialSummary } from '../../components/financial-summary/financial-summary';
import { ExpenseCharts } from '../../components/expense-charts/expense-charts';
import { ExpenseTable } from '../../components/expense-table/expense-table';
import { AiChat } from '../../../chat/ai-chat/ai-chat';
import { FiltrosChat } from '../../../../core/services/chat.service';


@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    FormsModule,
    FinancialSummary,
    ExpenseCharts,
    AiChat,
    ExpenseTable,
  ],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  filtrosChat: FiltrosChat = {
    ano_exercicio: 2025,
    cod_uo: null,
    nome_favorecido: null,
    situacao_pagamento: null,
    apenas_anomalias: false,
  };

  limparFiltros(): void {
    this.filtrosChat = {
      ano_exercicio: 2025,
      cod_uo: null,
      nome_favorecido: null,
      situacao_pagamento: null,
      apenas_anomalias: false,
    };
  }

  aplicarFiltros(): void {
  this.filtrosChat = { ...this.filtrosChat };
}
}
