# Adds HokieMacros' native pieces to the Capacitor-generated Xcode project:
#   - HMViewController + WidgetBridgePlugin in the App target
#   - the HokieWidget home screen widget (WidgetKit extension), embedded in the app
# Run from ios-app/ after `npx cap add ios`. Files are copied in by the workflow first.
require 'xcodeproj'

proj = Xcodeproj::Project.open('ios/App/App.xcodeproj')
app = proj.targets.find { |t| t.name == 'App' } or abort 'App target not found'

app_group = proj.main_group.children.find { |g| g.respond_to?(:path) && g.path == 'App' } or abort 'App group not found'
%w[HMViewController.swift WidgetBridgePlugin.swift].each do |f|
  next if app_group.files.any? { |r| r.path == f }
  app.add_file_references([app_group.new_reference(f)])
end
app.add_system_framework('WidgetKit')

if proj.targets.none? { |t| t.name == 'HokieWidget' }
  w = proj.new_target(:app_extension, 'HokieWidget', :ios, '16.0')
  wg = proj.main_group.new_group('HokieWidget', 'HokieWidget')
  w.add_file_references([wg.new_reference('HokieWidget.swift')])
  wg.new_reference('Info.plist')
  wg.new_reference('HokieWidget.entitlements')
  w.add_system_framework('WidgetKit')
  w.add_system_framework('SwiftUI')
  w.build_configurations.each do |c|
    s = c.build_settings
    s['PRODUCT_BUNDLE_IDENTIFIER'] = 'io.github.lucakane246.hokiemacros.widget'
    s['PRODUCT_NAME'] = '$(TARGET_NAME)'
    s['INFOPLIST_FILE'] = 'HokieWidget/Info.plist'
    s['GENERATE_INFOPLIST_FILE'] = 'NO'
    s['CODE_SIGN_ENTITLEMENTS'] = 'HokieWidget/HokieWidget.entitlements'
    s['CODE_SIGN_STYLE'] = 'Automatic'
    s['SWIFT_VERSION'] = '5.0'
    s['TARGETED_DEVICE_FAMILY'] = '1'
    s['IPHONEOS_DEPLOYMENT_TARGET'] = '16.0'
    s['SKIP_INSTALL'] = 'YES'
    s['APPLICATION_EXTENSION_API_ONLY'] = 'YES'
    s['LD_RUNPATH_SEARCH_PATHS'] = ['$(inherited)', '@executable_path/Frameworks', '@executable_path/../../Frameworks']
  end
  app.add_dependency(w)
  embed = app.copy_files_build_phases.find { |b| b.name == 'Embed Foundation Extensions' } ||
          app.new_copy_files_build_phase('Embed Foundation Extensions')
  embed.symbol_dst_subfolder_spec = :plug_ins
  bf = embed.add_file_reference(w.product_reference, true)
  bf.settings = { 'ATTRIBUTES' => ['RemoveHeadersOnCopy'] }
end

proj.save
puts "Targets: #{proj.targets.map(&:name).join(', ')}"
