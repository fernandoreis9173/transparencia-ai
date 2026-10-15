
import { Component } from '@angular/core';
import { FinancialSummary } from '../../components/financial-summary/financial-summary';
import { ExpenseCharts } from '../../components/expense-charts/expense-charts';
import { AiChat } from '../../../chat/ai-chat/ai-chat';
import { ExpenseTable } from '../../components/expense-table/expense-table';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
  FinancialSummary,
  ExpenseCharts,
  AiChat,
  ExpenseTable
],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
}
