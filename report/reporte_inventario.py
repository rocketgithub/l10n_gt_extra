# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from odoo.release import version_info
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
        fecha_desde = ''

        fecha_desde = str(fields.Date.to_date(datos['fecha_hasta']).strftime("%Y") + '-' + '01' + '-' + '01')
        account_ids = [x for x in datos['cuentas_id']]
        accounts_str = ','.join([str(x) for x in datos['cuentas_id']])

        if version_info[0] in [13, 14, 15]:
            include_initial_balance = 't.include_initial_balance'
            join_initial_balance = 'join account_account_type t on (t.id = a.user_type_id)'
            account_type = 't.id'
        else:
            include_initial_balance = 'a.include_initial_balance'
            join_initial_balance = ''
            account_type = 'a.account_type'

        self.env.cr.execute('select a.id, a.code as codigo, a.name as cuenta, ' + account_type + ' as id_cuenta, ' + include_initial_balance + ' as balance_inicial, sum(l.debit) as debe, sum(l.credit) as haber ' \
        	'from account_move_line l join account_account a on(l.account_id = a.id)' \
        	+ join_initial_balance + \
        	'where a.id in ('+accounts_str+') and l.date >= %s and l.date <= %s group by a.id, a.code, a.name, ' + account_type + ',' + include_initial_balance + ' ORDER BY a.code',
        (fecha_desde, datos['fecha_hasta']))

        for r in self.env.cr.dictfetchall():
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

            if version_info[0] in [13, 14, 15]:
                if r['id_cuenta'] in [1,3,5,6,7,8]:
                    lineas['activo'].append(linea)
                elif r['id_cuenta'] in [2,4,9,10]:
                    lineas['pasivo'].append(linea)
                elif r['id_cuenta'] in [11]:
                    lineas['capital'].append(linea)
            else:
                if r['id_cuenta'][0:5] == 'asset':
                    lineas['activo'].append(linea)
                elif r['id_cuenta'][0:9] == 'liability':
                    lineas['pasivo'].append(linea)
                elif r['id_cuenta'][0:6] == 'equity':
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

    def fecha_desde(self, datos):
        return str(fields.Date.to_date(datos['fecha_hasta']).strftime("%Y") + '-' + '01' + '-' + '01')

    @api.model
    def _get_report_values(self, docids, data=None):
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
            'current_company_id': self.env.company,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: