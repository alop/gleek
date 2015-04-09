# encoding: UTF-8

Vagrant.configure('2') do |config|
  config.vm.box = 'chef/fedora-20'
  config.vm.provision 'ansible' do |ansible|
    ansible.playbook = 'vagrant/site.yml'
    ansible.limit = 'all'
    ansible.sudo = true
    ansible.host_key_checking = false
    # ansible.verbose = "vvv"
  end

  config.vm.define 'gleek' do |c|
    c.vm.host_name = 'gleek'
    c.vm.provider 'virtualbox' do |vb|
      vb.customize ['modifyvm', :id, '--memory', '512']
    end
  end
end
