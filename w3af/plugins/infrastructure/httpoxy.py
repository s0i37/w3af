import w3af.core.data.constants.severity as severity

from w3af.core.controllers.plugins.infrastructure_plugin import InfrastructurePlugin
from w3af.core.data.options.opt_factory import opt_factory
from w3af.core.data.options.option_list import OptionList
from w3af.core.controllers.misc.decorators import runonce
from w3af.core.controllers.exceptions import RunOnce
from w3af.core.data.dc.headers import Headers
from w3af.core.data.kb.vuln import Vuln
import w3af.core.controllers.output_manager as om

from w3af.core.controllers.core_helpers.detect_resolve import Resolver


class httpoxy(InfrastructurePlugin):

	def __init__(self):
		InfrastructurePlugin.__init__(self)
		self._dns_zone = ''
		self._resolver = None

	def discover(self, fuzzable_request):
		if not self._dns_zone:
			om.out.debug("DNS zone not configured!")
			return

		self.fqdn_http_proxy = "prx.{target}.{domain}".format( target=fuzzable_request.get_uri().get_domain(), domain=self._dns_zone )

		url = fuzzable_request.get_url()
		headers = Headers( [ ('Proxy', 'http://%s:3128' % self.fqdn_http_proxy) ] )

		response = self._uri_opener.GET(url,
										cache=False,
										grep=False,
										headers=headers)

		if self.check('get.' + self.fqdn_http_proxy):
			desc = ('HTTP_PROXY inject detected.'
					'It is allows a MiTM attack')

			v = Vuln('HTTPoxy', desc, severity.HIGH, response.id,
					self.get_name())
			v.set_url(response.get_url())

			self.kb_append_uniq(self, 'httpoxy', v)

	def check(self, fqdn):
		return self._resolver.query(fqdn) != []

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
		Checks HTTP_PROXY environment injection via Proxy header.

		Only one configurable parameters exists:
		    - dns_zone
		"""