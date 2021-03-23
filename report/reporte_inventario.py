# -*- encoding: utf-8 -*-

from odoo import api, models, fields
import time
import datetime
import logging

class ReporteInventario(models.AbstractModel):
    _name = 'report.l10n_gt_extra.reporte_inventario'

    def retornar_saldo_inicial_todos_anios(self, cuenta, fecha_desde):
        saldo_inicial = 0
        self.env.cr.execute('select a.id, a.code as codigo, a.name as cuenta, sum(l.debit) as debe, sum(l.credit) as haber '\
        'from account_move_line l join account_account a on(l.account_id = a.id)'\
        'where a.id = %s and l.date < %s group by a.id, a.code, a.name,l.debit,l.credit', (cuenta,fecha_desde))
        for m in self.env.cr.dictfetchall():
            saldo_inicial += m['debe'] - m['haber']
        return saldo_inicial

    def retornar_saldo_inicial_inicio_anio(self, cuenta, fecha_desde):
        saldo_inicial = 0
        fecha = fields.Date.from_string(fecha_desde)
        self.env.cr.execute('select a.id, a.code as codigo, a.name as cuenta, sum(l.debit) as debe, sum(l.credit) as haber '\
        'from account_move_line l join account_account a on(l.account_id = a.id)'\
        'where a.id = %s and l.date < %s and l.date >= %s group by a.id, a.code, a.name,l.debit,l.credit', (cuenta,fecha_desde,fecha.strftime('%Y-1-1')))
        for m in self.env.cr.dictfetchall():
            saldo_inicial += m['debe'] - m['haber']
        return saldo_inicial

    def lineas(self, datos):
        totales = {}
        lineas_resumidas = {}
        lineas = {'activo':[],'total_activo': 0,'pasivo': [],'total_pasivo': 0,'capital': [],'total_capital': 0,}
        agrupado = {'activo':[],'pasivo': [],'capital': []}
        totales['debe'] = 0
        totales['haber'] = 0
        totales['saldo_inicial'] = 0
        totales['saldo_final'] = 0
        fecha_desde = self.fecha_desde(datos['fecha_hasta'])

        account_ids = [x for x in datos['cuentas_id']]


        accounts_str = ','.join([str(x) for x in datos['cuentas_id']])
        self.env.cr.execute('select a.id, a.code as codigo, a.name as cuenta,t.id as id_cuenta,t.include_initial_balance as balance_inicial, sum(l.debit) as debe, sum(l.credit) as haber ' \
        	'from account_move_line l join account_account a on(l.account_id = a.id)' \
        	'join account_account_type t on (t.id = a.user_type_id)' \
        	'where a.id in ('+accounts_str+') and l.date >= %s and l.date <= %s group by a.id, a.code, a.name,t.id,t.include_initial_balance ORDER BY a.code',
        (fecha_desde, datos['fecha_hasta']))

        dictfetchall = self.env.cr.dictfetchall()
        for cuenta in datos['cuentas_id']:
            existe = False
            for r in dictfetchall:
                if cuenta == r['id']:
                    existe = True
                    totales['debe'] += r['debe']
                    totales['haber'] += r['haber']
                    linea = {
                        'id': r['id'],
                        'codigo': r['codigo'],
                        'cuenta': r['cuenta'],
                        'saldo_inicial': 0,
                        'debe': r['debe'],
                        'haber': r['haber'],
                        'saldo_final': 0,
                        'balance_inicial': r['balance_inicial']
                    }

                    if r['id_cuenta'] in [self.env.ref('account.data_account_type_receivable').id,self.env.ref('account.data_account_type_liquidity').id,self.env.ref('account.data_account_type_current_assets').id,self.env.ref('account.data_account_type_fixed_assets').id]:
                        lineas['activo'].append(linea)
                    elif r['id_cuenta'] in [self.env.ref('account.data_account_type_credit_card').id,self.env.ref('account.data_account_type_current_liabilities').id,self.env.ref('account.data_account_type_non_current_liabilities').id]:
                        lineas['pasivo'].append(linea)
                    elif r['id_cuenta'] in [self.env.ref('account.data_account_type_equity').id]:
                        lineas['capital'].append(linea)

            if not existe:
                cuenta_id = self.env['account.account'].search([('id','=',cuenta)])
                linea = {
                    'id': cuenta_id.id,
                    'codigo': cuenta_id.code,
                    'cuenta': cuenta_id.name,
                    'saldo_inicial': 0,
                    'debe': 0,
                    'haber': 0,
                    'saldo_final': 0,
                    'balance_inicial': 0
                }

                if cuenta_id.user_type_id.id in [self.env.ref('account.data_account_type_receivable').id,self.env.ref('account.data_account_type_liquidity').id,self.env.ref('account.data_account_type_current_assets').id,self.env.ref('account.data_account_type_fixed_assets').id]:
                    lineas['activo'].append(linea)
                elif cuenta_id.user_type_id.id in [self.env.ref('account.data_account_type_credit_card').id,self.env.ref('account.data_account_type_current_liabilities').id,self.env.ref('account.data_account_type_non_current_liabilities').id]:
                    lineas['pasivo'].append(linea)
                elif cuenta_id.user_type_id.id in [self.env.ref('account.data_account_type_equity').id]:
                    lineas['capital'].append(linea)

        for l in lineas['activo']:
            if not l['balance_inicial']:
                l['saldo_inicial'] += self.retornar_saldo_inicial_inicio_anio(l['id'], fecha_desde)
                l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                totales['saldo_inicial'] += l['saldo_inicial']
                totales['saldo_final'] += l['saldo_final']
            else:
                l['saldo_inicial'] += self.retornar_saldo_inicial_todos_anios(l['id'], fecha_desde)
                l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                totales['saldo_inicial'] += l['saldo_inicial']
                totales['saldo_final'] += l['saldo_final']

        for l in lineas['pasivo']:
            if not l['balance_inicial']:
                l['saldo_inicial'] += self.retornar_saldo_inicial_inicio_anio(l['id'], fecha_desde)
                l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                totales['saldo_inicial'] += l['saldo_inicial']
                totales['saldo_final'] += l['saldo_final']
            else:
                l['saldo_inicial'] += self.retornar_saldo_inicial_todos_anios(l['id'], fecha_desde)
                l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                totales['saldo_inicial'] += l['saldo_inicial']
                totales['saldo_final'] += l['saldo_final']

        for l in lineas['capital']:
            if not l['balance_inicial']:
                l['saldo_inicial'] += self.retornar_saldo_inicial_inicio_anio(l['id'], fecha_desde)
                l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                totales['saldo_inicial'] += l['saldo_inicial']
                totales['saldo_final'] += l['saldo_final']
            else:
                l['saldo_inicial'] += self.retornar_saldo_inicial_todos_anios(l['id'], fecha_desde)
                l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                totales['saldo_inicial'] += l['saldo_inicial']
                totales['saldo_final'] += l['saldo_final']

        return {'lineas': lineas,'totales': totales }

    def fecha_desde(self,fecha_hasta):
        anio = str(datetime.datetime.strptime(str(fecha_hasta), '%Y-%m-%d').date().strftime('%Y'))
        fecha_desde =  str(anio + '-' + '01' + '-' + '01')
        return fecha_desde

    @api.model
    def _get_report_values(self, docids, data=None):
        return self.get_report_values(docids, data)

    @api.model
    def get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        diario = self.env['account.move.line'].browse(data['form']['cuentas_id'][0])

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'lineas': self.lineas,
            'fecha_desde': self.fecha_desde,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
